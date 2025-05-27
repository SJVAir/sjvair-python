import calendar
import concurrent.futures
import csv
import datetime
import functools
import json
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

from queue import Queue
from random import random

MONITOR_CSV = 'sjvair-monitor-list.csv'
RESULTS_CSV = 'data-export.csv'

START_DATE = datetime.date(2024, 1, 1)
END_DATE = datetime.date(2024, 12, 31)

SENSORS = ['a', 'b'] # Comment out to fetch default sensors

API_URL = 'https://www.sjvair.com/api/1.0/'

HEADERS = (
  'timestamp', 'sensor', 'celsius', 'fahrenheit', 'humidity', 'pressure',
  'pm10', 'pm25', 'pm100', 'pm25_reported', 'pm25_avg_15', 'pm25_avg_60',
  'particles_03um', 'particles_05um', 'particles_100um',
  'particles_10um', 'particles_25um', 'particles_50um',
  'monitor_id', 'position', 'is_sjvair', 'name', 'default_sensor',
  'pm25_calibration_formula'
)


# --------------------------------------------------------------------------- #


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

    chunks = [(
        datetime.datetime.combine(start_date, datetime.time.min),
        datetime.datetime.combine(end_date, datetime.time.max),
    ) for (start_date, end_date) in chunks]

    return chunks


def fetch_entries(queue, idx, monitor, start_time, end_time, sensor=None, page=1, retry=5):
    print(f'fetch_entries({idx}: {monitor["id"]}, {start_time.date()}, {end_time.date()}, {sensor}, {page}, {retry})')
    params = {
        'timestamp__gte': start_time,
        'timestamp__lte': end_time,
        'page': page,
        'fields': ','.join(HEADERS),
    }
    if sensor is not None:
        # If the sensor is None, it will default to the default sensor.
        params['sensor'] = sensor

    url = f'{API_URL}monitors/{monitor["id"]}/entries/?{urllib.parse.urlencode(params)}'

    try:
        response = urllib.request.urlopen(url)
    except urllib.error.URLError as err:
        # Retry logic for failed requests
        if retry > 0:
            backoff = (6 - retry) ** 3
            print('\n'.join([
                f'... fetch_entries({idx}: {monitor["id"]}, {start_time.date()}, {end_time.date()}, {sensor}, {page}, {retry})',
                f'... > {getattr(err, "code", "Error")}: {err.reason}, retrying in {backoff} seconds...',
            ]))
            time.sleep(backoff)
            return fetch_entries(
                queue=queue,
                idx=idx,
                monitor=monitor,
                start_time=start_time,
                end_time=end_time,
                sensor=sensor,
                page=page,
                retry=retry - 1
            )
        raise err

    # Read the response and parse the JSON data
    data = json.loads(response.read())

    # If there are more pages, add the next page to the queue
    if data['has_next_page']:
        queue.put(dict(
            idx=idx,
            monitor=monitor,
            start_time=start_time,
            end_time=end_time,
            sensor=sensor,
            page=page + 1 # Next page!
        ))

    return [dict({
        'monitor_id': monitor['id'],
        'position': monitor['position'],
        'is_sjvair': monitor['is_sjvair'],
        'name': monitor['name'],
        'default_sensor': monitor['default_sensor'],
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
    with open(RESULTS_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        while True:
            if write_queue.is_shutdown:
                break

            if write_queue.empty():
                time.sleep(1)
                continue

            entries = write_queue.get()
            writer.writerows([{k: entry[k] for k in HEADERS} for entry in entries])
            write_queue.task_done()
    print('Writer stopped!')


def main():
    '''
        Fetch entries for all monitors in the MONITOR_CSV file between the
        START_DATE and END_DATE and specified SENSORS, and write the results
        to the RESULTS_CSV.
    '''

    TIMER_START = time.time()

    date_chunks = chunk_date_range(START_DATE, END_DATE)
    sensors = globals().get('SENSORS', [None])

    print()
    print('MONITOR_CSV:', MONITOR_CSV)
    print('RESULTS_CSV:', RESULTS_CSV)
    print('SENSORS:', sensors if 'SENSORS' in globals() else 'default')
    print('START_TIME:', START_DATE)
    print('END_TIME:', END_DATE)
    print('DATE_CHUNKS:')
    for start, end in date_chunks:
        print(f'\t{start.date()} - {end.date()}')
    print()


    work_queue = Queue() # entries to fetch
    write_queue = Queue() # fetched entries to write

    # Open the MONITOR_CSV file and seed the work queue.
    print('Loading the work queue...')
    with open(MONITOR_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for idx, monitor in enumerate(reader):
            for sensor in sensors:
                for start_date, end_date in date_chunks:
                    work_queue.put({
                        'idx': idx,
                        'monitor': monitor,
                        'start_time': start_date,
                        'end_time': end_date,
                        'sensor': sensor,
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
