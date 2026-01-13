import calendar
import concurrent.futures
import csv
import datetime
import functools
import json
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

from pathlib import Path
from queue import Queue
from typing import Iterable

MONITOR_CSV = 'sjvair-monitor-list.csv'
RESULTS_CSV = 'data-export.csv'

START_DATE = datetime.date(2025, 1, 1)
END_DATE = datetime.date(2025, 3, 1)

# Default stage and calibration per pollutant
# SCOPE = 'resolved'

# All stages and calibrations per pollutant
SCOPE = 'expanded'

API_URL = 'https://www.sjvair.com/api/2.0/'


# --------------------------------------------------------------------------- #

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


def print_traceback(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            raise
    return wrapper


def chunk_date_range(start_date, end_date):
    '''Splits a date range into chunks, one for each month.'''

    chunks = []
    current_date = start_date
    while current_date <= end_date:
        month = current_date.month
        year = current_date.year
        last_day = calendar.monthrange(year, month)[1]
        month_end_date = datetime.date(year, month, last_day)
        chunk_end_date = min(month_end_date, end_date)
        chunks.append((current_date, chunk_end_date))
        current_date = chunk_end_date + datetime.timedelta(days=1)

    chunks = [(start_date, end_date) for (start_date, end_date) in chunks]

    return chunks


def iter_ndjson(path: Path) -> Iterable[dict]:
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def fetch_entries(queue, idx, monitor, start_date, end_date, retry=5):
    print(f'fetch_entries({idx}: {monitor["id"]}, {start_date}, {end_date}, {retry})')
    params = {
        'start_date': start_date,
        'end_date': end_date,
        'scope': 'expanded',
    }

    url = f'{API_URL}monitors/{monitor["id"]}/entries/export/json/?{urllib.parse.urlencode(params)}'

    try:
        response = urllib.request.urlopen(url)
    except urllib.error.URLError as err:
        # Retry logic for failed requests
        if retry > 0:
            backoff = (6 - retry) ** 3
            print('\n'.join([
                f'... fetch_entries({idx}: {monitor["id"]}, {start_date}, {end_date}, {retry})',
                f'... > {getattr(err, "code", "Error")}: {err.reason}, retrying in {backoff} seconds...',
            ]))
            time.sleep(backoff)
            return fetch_entries(
                queue=queue,
                idx=idx,
                monitor=monitor,
                start_date=start_date,
                end_date=end_date,
                retry=retry - 1
            )
        raise err

    # Read the response and parse the JSON data
    data = json.loads(response.read())

    longitude, latitude = parse_ewkt_point(monitor['position'])

    return [dict({
        'monitor_id': monitor['id'],
        'longitude': longitude,
        'latitude': latitude,
        'is_sjvair': monitor['is_sjvair'],
        'name': monitor['name'],
    }, **entry) for entry in data['data']]


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


def main():
    '''
        Fetch entries for all monitors in the MONITOR_CSV file between the
        START_DATE and END_DATE, and write the results to the RESULTS_CSV.
    '''

    TIMER_START = time.time()

    date_chunks = chunk_date_range(START_DATE, END_DATE)

    print()
    print('MONITOR_CSV:', MONITOR_CSV)
    print('RESULTS_CSV:', RESULTS_CSV)
    print('START_DATE:', START_DATE)
    print('END_DATE:', END_DATE)
    print('DATE_CHUNKS:')
    for start, end in date_chunks:
        print(f'\t{start} - {end}')
    print()


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
    for x in range(10):
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
