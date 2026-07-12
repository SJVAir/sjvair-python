# CalHeatScore

Daily ZIP-code-level heat-risk scores (0–4) from CalEPA's CalHeatScore, covering San Joaquin Valley ZIP codes.

## `calheatscore`

No flags returns today's score for every SJV ZIP code. `--date` scopes to a specific date; `--zip` scopes to a specific ZIP's full history (past actuals + forecast); combine both for one ZIP on one date.

```bash
sjvair calheatscore
```

```bash
sjvair calheatscore --date 2026-07-13
```

```bash
sjvair calheatscore --zip 93728
```

```bash
sjvair calheatscore --zip 93728 --date 2026-07-13
```
