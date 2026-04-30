import argparse
import concurrent.futures
import csv
import dataclasses
import datetime
import functools
import json
import random
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

# Final CSV export written after all period chunks are concatenated
RESULTS_CSV = 'data-export.csv'


# --- Export time range

# Inclusive start date for the export
START_DATE = datetime.date(2025, 1, 1)

# Inclusive end date for the export
END_DATE = datetime.date(2025, 12, 31)


# --- Export scope / data shape

# Export only the default stage + calibration per pollutant
# SCOPE = 'resolved'

# Export all stages, sensors, processors, and calibrations per pollutant
SCOPE = 'expanded'


# --- Period chunking
# The full date range is split into periods. Each period is fetched, written
# to a chunked CSV, and the staging NDJSON is deleted before the next period
# starts — keeping disk usage bounded.

# Number of months per outer period chunk
MONTHS_PER_PERIOD = 1


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
# CONFIG

@dataclasses.dataclass
class ExportConfig:
    output: str
    build_dir: Path
    start_date: datetime.date
    end_date: datetime.date
    scope: str
    period_months: int
    sort: bool


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


def print_settings(config: ExportConfig, period_chunks):
    print()
    print('=== SJVAir Data Export Configuration ===')

    print('\n[Files]')
    print(f'  results_csv       : {config.output}')
    print(f'  build_dir         : {config.build_dir}')

    print('\n[Date Range]')
    print(f'  start_date        : {config.start_date}')
    print(f'  end_date          : {config.end_date}')
    print(f'  months_per_period : {config.period_months}')
    print(f'  days_per_request  : {DAYS_PER_REQUEST}')
    print('  period_chunks:')
    for start, end in period_chunks:
        print(f'    - {start} -> {end}')

    print('\n[Export Scope]')
    print(f'  scope             : {config.scope}')

    print('\n[Load Shaping]')
    print(f'  max_workers       : {MAX_WORKERS}')
    print(f'  max_connections   : {MAX_CONNECTIONS}')
    print(f'  request_retries   : {REQUEST_RETRIES}')

    print('\n[API]')
    print(f'  api_url           : {API_URL}')
    print(f'  retryable_status  : {sorted(RETRYABLE_STATUS)}')

    print('\n========================================\n')


def chunk_date_range(start_date, end_date, days=DAYS_PER_REQUEST):
    '''Splits a date range into chunks, each `days` long.'''
    chunks = []
    current_date = start_date
    while current_date <= end_date:
        period_end_date = current_date + datetime.timedelta(days=days - 1)
        chunk_end_date = min(period_end_date, end_date)
        chunks.append((current_date, chunk_end_date))
        current_date = chunk_end_date + datetime.timedelta(days=1)
    return chunks


def chunk_by_months(start_date, end_date, months=1):
    '''Splits a date range into periods of `months` months each.'''
    chunks = []
    current = start_date
    while current <= end_date:
        # Advance by `months` months
        advance = current.month - 1 + months
        next_year = current.year + advance // 12
        next_month = advance % 12 + 1
        next_start = datetime.date(next_year, next_month, 1)
        chunk_end = min(next_start - datetime.timedelta(days=1), end_date)
        chunks.append((current, chunk_end))
        current = next_start
    return chunks


def period_paths(build_dir: Path, output_csv: str, start: datetime.date, end: datetime.date) -> tuple[Path, Path]:
    '''Returns (ndjson_path, chunk_csv_path) for a given period.'''
    stem = Path(output_csv).stem
    tag = f'{start}_{end}'
    return build_dir / f'{stem}.{tag}.ndjson', build_dir / f'{stem}.{tag}.csv'


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


def parse_point(value) -> tuple[float, float]:
    # GeoJSON: {"type": "Point", "coordinates": [lon, lat]}
    try:
        coords = value['coordinates']
        return float(coords[0]), float(coords[1])
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


def fetch_monitor(monitor_id: str) -> dict:
    url = f'{API_URL}monitors/{monitor_id}/'
    response = fetch_json(url)
    return response.get('data', response)


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

def fetch_entries(queue, idx, monitor, start_date, end_date, scope):
    params = {
        'start_date': start_date,
        'end_date': end_date,
        'scope': scope,
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

    longitude, latitude = parse_point(monitor['position'])

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
def write_ndjson_task(write_queue, ndjson_path: Path):
    '''Write fetched entries to an NDJSON staging file.'''
    print(f'Writer started: {ndjson_path}')

    seen_keys: set[str] = set()

    with ndjson_path.open('w', encoding='utf-8', newline='\n') as f:
        while True:
            if write_queue.is_shutdown:
                break

            if write_queue.empty():
                time.sleep(1)
                continue

            entries = write_queue.get()
            for entry in entries:
                seen_keys.update(entry.keys())
                f.write(json.dumps(entry, separators=(',', ':')))
                f.write('\n')
                f.flush()

            write_queue.task_done()

    print(f'Writer finished: {ndjson_path}')
    return seen_keys


# --------------------------------------------------------------------------- #
# PERIOD RUNNER

def run_period(config: ExportConfig, monitors, start_date, end_date, ndjson_path: Path, chunk_csv: Path):
    '''Fetch all monitors for one period, write chunked CSV, clean up NDJSON.'''
    date_chunks = chunk_date_range(start_date, end_date)

    work_queue = Queue()
    write_queue = Queue()

    for idx, monitor in enumerate(monitors):
        for chunk_start, chunk_end in date_chunks:
            work_queue.put({
                'idx': idx,
                'monitor': monitor,
                'start_date': chunk_start,
                'end_date': chunk_end,
                'scope': config.scope,
            })

    print(f'  Queue size: {work_queue.qsize()}')

    executor = concurrent.futures.ThreadPoolExecutor()
    for _ in range(MAX_WORKERS):
        executor.submit(work_task, work_queue, write_queue)

    write_future = executor.submit(write_ndjson_task, write_queue, ndjson_path)

    work_queue.join()
    print('  Downloading complete.')

    write_queue.join()
    print('  Writing NDJSON complete.')

    work_queue.shutdown()
    write_queue.shutdown()
    executor.shutdown()

    seen_keys = write_future.result()

    # Roll up NDJSON → chunked CSV, then delete NDJSON
    print(f'  Rolling up to CSV: {chunk_csv}')
    headers = build_csv_headers(seen_keys)
    with chunk_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore', quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()

        rows = iter_ndjson(ndjson_path)
        if config.sort:
            rows = sorted(rows, key=lambda r: r.get('timestamp', ''))
        for entry in rows:
            writer.writerow(entry)

    ndjson_path.unlink(missing_ok=True)
    print(f'  Chunk complete: {chunk_csv}')


# --------------------------------------------------------------------------- #
# FINAL CONCAT

def concat_chunks(config: ExportConfig, chunk_csvs: list[Path]):
    '''Concatenate all chunked CSVs into the final output CSV.'''
    print(f'\nConcatenating {len(chunk_csvs)} chunk(s) into {config.output}...')

    # Collect the union of all headers (preserving static column order)
    seen_keys: set[str] = set()
    for path in chunk_csvs:
        with path.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            seen_keys.update(reader.fieldnames or [])

    headers = build_csv_headers(seen_keys)

    with open(config.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore', quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()

        # Stream chunks in order — no full in-memory sort at this scale.
        # --sort already sorted each chunk during the per-period rollup.
        for path in chunk_csvs:
            with path.open('r', encoding='utf-8') as cf:
                for row in csv.DictReader(cf):
                    writer.writerow(row)

    print(f'Final CSV written: {config.output}')


# --------------------------------------------------------------------------- #
# MAIN

def main():
    '''
        Fetch entries for the given monitors between START_DATE and END_DATE,
        broken into monthly (or N-month) periods. Each period is staged as a
        chunked CSV; existing chunks are skipped so the run can resume after
        a crash or network outage. All chunks are concatenated into the final
        output CSV at the end.
    '''

    parser = argparse.ArgumentParser(description='SJVAir data export')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--monitors', nargs='+', metavar='ID', help='One or more monitor IDs')
    source.add_argument('--csv', metavar='FILE', help='CSV file with an "id" column')
    parser.add_argument('--output', metavar='FILE', default=RESULTS_CSV, help=f'Output CSV file (default: {RESULTS_CSV})')
    parser.add_argument('--start-date', metavar='YYYY-MM-DD', default=START_DATE, type=datetime.date.fromisoformat, help=f'Inclusive start date (default: {START_DATE})')
    parser.add_argument('--end-date', metavar='YYYY-MM-DD', default=END_DATE, type=datetime.date.fromisoformat, help=f'Inclusive end date (default: {END_DATE})')
    parser.add_argument('--scope', default=SCOPE, choices=['resolved', 'expanded'], help=f'Export scope (default: {SCOPE})')
    parser.add_argument('--period-months', metavar='N', default=MONTHS_PER_PERIOD, type=int, help=f'Months per period chunk (default: {MONTHS_PER_PERIOD})')
    parser.add_argument('--build-dir', metavar='DIR', default=None, help='Directory for staging files (default: <output-stem>-build/)')
    parser.add_argument('--sort', action='store_true', help='Sort output by timestamp (loads all rows into memory at concat step)')
    args = parser.parse_args()

    TIMER_START = time.time()

    build_dir = Path(args.build_dir) if args.build_dir else Path(Path(args.output).stem + '-build')
    build_dir.mkdir(parents=True, exist_ok=True)

    config = ExportConfig(
        output=args.output,
        build_dir=build_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        scope=args.scope,
        period_months=args.period_months,
        sort=args.sort,
    )

    period_chunks = chunk_by_months(config.start_date, config.end_date, config.period_months)
    print_settings(config, period_chunks)

    # Collect monitor IDs from whichever source was given.
    if args.monitors:
        monitor_ids = args.monitors
    else:
        with open(args.csv, 'r', encoding='utf-8-sig') as cf:
            monitor_ids = [row['id'] for row in csv.DictReader(cf)]

    # Fetch full monitor details from the API.
    print('Fetching monitor details...')
    monitors = []
    for idx, monitor_id in enumerate(monitor_ids):
        print(f'  {idx}.  {monitor_id}')
        monitors.append(fetch_monitor(monitor_id))

    # Process each period chunk, skipping any that already have a CSV on disk.
    chunk_csvs = []
    for period_start, period_end in period_chunks:
        ndjson_path, chunk_csv = period_paths(config.build_dir, config.output, period_start, period_end)
        chunk_csvs.append(chunk_csv)

        if chunk_csv.exists():
            print(f'\n[{period_start} -> {period_end}] Already fetched, skipping. ({chunk_csv.name})')
            continue

        print(f'\n[{period_start} -> {period_end}] Starting...')
        run_period(config, monitors, period_start, period_end, ndjson_path, chunk_csv)

    # Concatenate all chunked CSVs into the final output.
    concat_chunks(config, chunk_csvs)

    TIMER_END = time.time()
    print(f'\nCompleted in {datetime.timedelta(seconds=TIMER_END - TIMER_START)}.')


if __name__ == '__main__':
    main()
