
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[4]

CASE_DIR = (
    PROJECT_ROOT
    / "datasets"
    / "model B"
    / "raw"
    / "RCAEval"
    / "re2tt_ts-order-service_delay_2"
)


def show_timeline(name, timestamps, injection_time):
    timestamps = pd.to_numeric(timestamps, errors="coerce").dropna()

    if timestamps.empty:
        print(f"\n{name}: no valid timestamps found.")
        return

    before = (timestamps < injection_time).sum()
    after = (timestamps >= injection_time).sum()

    print(f"\n{name}")
    print("-" * 50)
    print(f"Valid timestamp records: {len(timestamps):,}")
    print(f"Earliest timestamp (UTC): "
          f"{pd.to_datetime(timestamps.min(), unit='s', utc=True)}")
    print(f"Latest timestamp (UTC):   "
          f"{pd.to_datetime(timestamps.max(), unit='s', utc=True)}")
    print(f"Before injection: {before:,}")
    print(f"At or after injection: {after:,}")


def main():
    injection_path = CASE_DIR / "inject_time.txt"

    if not injection_path.exists():
        raise FileNotFoundError(injection_path)

    injection_time = int(injection_path.read_text().strip())

    print("FAULT INJECTION TIME")
    print("-" * 50)
    print(f"Unix timestamp: {injection_time}")
    print(
        "UTC time:",
        pd.to_datetime(injection_time, unit="s", utc=True),
    )

    metrics_path = CASE_DIR / "metrics.parquet"
    logs_path = CASE_DIR / "logs.parquet"
    traces_path = CASE_DIR / "traces.parquet"

    # Metrics timestamps are in seconds, according to the sample.
    metrics = pd.read_parquet(metrics_path)
    show_timeline("METRICS", metrics["time"], injection_time)

    # Log timestamps also appear to be Unix seconds.
    logs = pd.read_parquet(logs_path)
    show_timeline("LOGS", logs["timestamp"], injection_time)

    # Trace startTimeMillis appears to be milliseconds.
    traces = pd.read_parquet(traces_path)
    trace_seconds = traces["startTimeMillis"] / 1000
    show_timeline("TRACES (using startTimeMillis)", trace_seconds,
                  injection_time)

    # Report missingness without deleting any data.
    print("\nFULLY MISSING METRIC COLUMNS")
    print("-" * 50)
    missing_fraction = metrics.isna().mean()
    fully_missing = missing_fraction[missing_fraction == 1.0]

    if fully_missing.empty:
        print("None")
    else:
        for column in fully_missing.index:
            print(f"{column}: 100% missing")

    print("\nTRACE MISSINGNESS")
    print("-" * 50)
    print(traces.isna().sum().to_string())

    print("\nTIMELINE CHECK COMPLETE")
    print("No source files were modified.")


if __name__ == "__main__":
    main()
