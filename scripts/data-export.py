import concurrent.futures
import csv
import datetime
import functools
import json
import random
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

from pathlib import Path
from queue import Queue
from typing import Iterable

# --------------------------------------------------------------------------- #
# CONFIGURATION

# --- Input / output files

# CSV containing the list of monitors to export (one row per monitor)
MONITOR_CSV = 'sjvair-monitor-list.csv'

# Final CSV export written after NDJSON staging
RESULTS_CSV = 'data-export.csv'


# --- Export time range

# Inclusive start date for the export
START_DATE = datetime.date(2025, 1, 1)

# Inclusive end date for the export
END_DATE = datetime.date(2025, 3, 1)


# --- Export scope / data shape

# Export only the default stage + calibration per pollutant
# SCOPE = 'resolved'

# Export all stages, sensors, processors, and calibrations per pollutant
SCOPE = 'expanded'


# --- Load shaping and concurrency tuning
# These values are intentionally conservative to avoid overloading the API.

# Number of worker threads pulling tasks from the queue
MAX_WORKERS = 10

# Maximum number of in-flight HTTP requests at any given time
MAX_CONNECTIONS = 4

# Number of days of data requested per API call
# Smaller values reduce response size and server-side processing cost
DAYS_PER_REQUEST = 7

# Number of retry attempts for transient failures
REQUEST_RETRIES = 5


# --- Network / API behavior

# Base URL for the SJVAir API
API_URL = 'https://www.sjvair.com/api/2.0/'

# HTTP status codes treated as transient and eligible for retry/backoff
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


# --------------------------------------------------------------------------- #
# UTILITIES

def print_traceback(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            raise
    return wrapper


def print_settings(date_chunks: list[tuple[datetime.date, datetime.date]]) -> None:
    print()
    print('=== SJVAir Data Export Configuration ===')

    print('\n[Files]')
    print(f'  monitor_csv      : {MONITOR_CSV}')
    print(f'  results_csv      : {RESULTS_CSV}')

    print('\n[Date Range]')
    print(f'  start_date       : {START_DATE}')
    print(f'  end_date         : {END_DATE}')
    print(f'  days_per_request : {DAYS_PER_REQUEST}')
    print('  date_chunks:')
    for start, end in date_chunks:
        print(f'    - {start} -> {end}')

    print('\n[Export Scope]')
    print(f'  scope            : {SCOPE}')

    print('\n[Load Shaping]')
    print(f'  max_workers      : {MAX_WORKERS}')
    print(f'  max_connections  : {MAX_CONNECTIONS}')
    print(f'  request_retries  : {REQUEST_RETRIES}')

    print('\n[API]')
    print(f'  api_url          : {API_URL}')
    print(f'  retryable_status : {sorted(RETRYABLE_STATUS)}')

    print('\n========================================\n')


def chunk_date_range(start_date, end_date, days=DAYS_PER_REQUEST):
    '''Splits a date(time) range into chunks, each `days` long.'''

    chunks = []
    current_date = start_date

    while current_date <= end_date:
        period_end_date = current_date + datetime.timedelta(days=days - 1)
        chunk_end_date = min(period_end_date, end_date)
        chunks.append((current_date, chunk_end_date))
        current_date = chunk_end_date + datetime.timedelta(days=1)

    return chunks


def iter_ndjson(path: Path) -> Iterable[dict]:
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


# --------------------------------------------------------------------------- #
# CSV HANDLING

STATIC_HEADERS = [
    'monitor_id',
    'name',
    'is_sjvair',
    'latitude',
    'longitude',
    'timestamp_local',
    'timestamp',
]


def build_csv_headers(seen_keys: set[str]) -> list[str]:
    # Keep your known "identity" columns first, then the rest sorted.
    dynamic = sorted(k for k in seen_keys if k not in STATIC_HEADERS)
    return [k for k in STATIC_HEADERS if k in seen_keys] + dynamic


def parse_ewkt_point(value: str) -> tuple[float, float]:
    # Expected: SRID=4326;POINT (lon lat)
    try:
        _, point = value.split(';', 1)
        coords = point.strip().lstrip('POINT').strip(' ()')
        lon_str, lat_str = coords.split()
        return float(lon_str), float(lat_str)
    except Exception:
        return None, None


# --------------------------------------------------------------------------- #
# REQUEST HANDLING

class CooldownGate:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._until = 0.0

    def wait(self) -> None:
        with self._lock:
            until = self._until
        now = time.monotonic()
        if now < until:
            time.sleep(until - now)

    def trip(self, seconds: float) -> None:
        # Extend cooldown, do not shorten it
        with self._lock:
            self._until = max(self._until, time.monotonic() + seconds + random.random() * 0.5)


IN_FLIGHT = threading.BoundedSemaphore(MAX_CONNECTIONS)
COOLDOWN = CooldownGate()


def fetch_json(url: str, timeout: int = 30) -> dict:
    COOLDOWN.wait()
    with IN_FLIGHT:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    # If the body is truncated/invalid JSON, this will raise JSONDecodeError.
    return json.loads(body)


def parse_retry_after(err: urllib.error.HTTPError) -> float | None:
    value = err.headers.get('Retry-After')
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# CORE FETCHING LOGIC

def fetch_entries(queue, idx, monitor, start_date, end_date):
    params = {
        'start_date': start_date,
        'end_date': end_date,
        'scope': SCOPE,
    }

    url = f'{API_URL}monitors/{monitor["id"]}/entries/export/json/?{urllib.parse.urlencode(params)}'

    for attempt in range(REQUEST_RETRIES):
        print(f'fetch_entries({idx}: {monitor["id"]}, {start_date}, {end_date}, {attempt})')

        try:
            data = fetch_json(url)
            break
        except urllib.error.HTTPError as err:
            if err.code not in RETRYABLE_STATUS or attempt >= REQUEST_RETRIES:
                raise
            backoff = (parse_retry_after(err) or (2 ** attempt)) + random.random()
            print(f'... {getattr(err, "code", "HTTPError")}: {err.reason} | retrying in {backoff:.1f}s ({attempt+1}/{REQUEST_RETRIES})')
            COOLDOWN.trip(backoff)
        except (TimeoutError, json.JSONDecodeError, urllib.error.URLError) as err:
            # Almost always a partial response under load.
            if attempt >= REQUEST_RETRIES:
                raise
            backoff = (2 ** attempt) + random.random()
            print(f'... {err.__class__.__name__}: retrying in {backoff:.1f}s ({attempt+1}/{REQUEST_RETRIES})')
            COOLDOWN.trip(backoff)
    else:
        raise RuntimeError(f'Failed after {REQUEST_RETRIES} attempts: {url}')

    longitude, latitude = parse_ewkt_point(monitor['position'])

    return [dict({
        'monitor_id': monitor['id'],
        'longitude': longitude,
        'latitude': latitude,
        'is_sjvair': monitor['is_sjvair'],
        'name': monitor['name'],
    }, **entry) for entry in data['data']]


# --------------------------------------------------------------------------- #
# THREAD TASKS

@print_traceback
def work_task(work_queue, write_queue):
    print('Worker started!')
    while True:
        if work_queue.is_shutdown:
            break

        if work_queue.empty():
            time.sleep(1)
            continue

        item = work_queue.get()
        entries = fetch_entries(queue=work_queue, **item)

        write_queue.put(entries)
        work_queue.task_done()

    print('Worker stopped!')


@print_traceback
def write_task(write_queue):
    print('Writer started!')

    seen_keys: set[str] = set()

    # Pass 1: write NDJSON to a temp file and collect keys
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='-sjvair.ndjson', encoding='utf-8', newline='\n') as tmp:
        tmp_path = Path(tmp.name)
        print(f'Writing to tempfile: {tmp_path}')

        while True:
            if write_queue.is_shutdown:
                break

            if write_queue.empty():
                time.sleep(1)
                continue

            entries = write_queue.get()
            for entry in entries:
                seen_keys.update(entry.keys())
                tmp.write(json.dumps(entry, separators=(',', ':')))
                tmp.write('\n')
                tmp.flush()

            write_queue.task_done()

    print('Finished writing to tempfile, building CSV.')

    # Pass 2: write final CSV
    headers = build_csv_headers(seen_keys)
    with open(RESULTS_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()

        for entry in iter_ndjson(tmp_path):
            # DictWriter will write blank for missing keys automatically
            writer.writerow(entry)

    try:
        tmp_path.unlink(missing_ok=True)
    except Exception:
        pass

    print('Writer finished!')


# --------------------------------------------------------------------------- #
# MAIN

def main():
    '''
        Fetch entries for all monitors in the MONITOR_CSV file between the
        START_DATE and END_DATE, and write the results to the RESULTS_CSV.
    '''

    TIMER_START = time.time()

    date_chunks = chunk_date_range(START_DATE, END_DATE)
    print_settings(date_chunks)

    work_queue = Queue() # entries to fetch
    write_queue = Queue() # fetched entries to write

    # Open the MONITOR_CSV file and seed the work queue.
    print('Loading the work queue...')
    with open(MONITOR_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for idx, monitor in enumerate(reader):
            for start_date, end_date in date_chunks:
                work_queue.put({
                    'idx': idx,
                    'monitor': monitor,
                    'start_date': start_date,
                    'end_date': end_date,
            })

    # Start the thread pool that will fetch the entries
    executor = concurrent.futures.ThreadPoolExecutor()
    for x in range(MAX_WORKERS):
        executor.submit(work_task, work_queue, write_queue)

    # Start the thread that will write the results to disk
    executor.submit(write_task, write_queue)

    # Wait for all the work to be done, then wrap it up.
    work_queue.join()
    print('Downloading complete.')

    write_queue.join()
    print('Writing complete.')

    print('Cleaning up and shutting down.')
    work_queue.shutdown()
    write_queue.shutdown()
    executor.shutdown()

    TIMER_END = time.time()
    print(f'Completed in {datetime.timedelta(seconds=TIMER_END - TIMER_START)}.')


if __name__ == '__main__':
    main()
