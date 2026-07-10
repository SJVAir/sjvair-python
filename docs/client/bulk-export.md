# Bulk export

For long date ranges, use `ExportEngine` — it splits the range into chunks (each within the server's 180-day export limit), downloads them concurrently, and merges the results. Interrupted runs can be resumed by re-running the same command (chunks that already have staging files are skipped):

```python
from pathlib import Path
from sjvair import SJVAirClient
from sjvair.export.engine import ExportEngine

with SJVAirClient() as client:
    engine = ExportEngine(client, output=Path('fresno-pm25.csv'))
    engine.run(monitor_ids=['id-1', 'id-2'], start_date='2020-01-01', end_date='2023-12-31')
```
