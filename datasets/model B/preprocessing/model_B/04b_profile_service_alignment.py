
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

METRIC_SUFFIXES = [
    "_latency-50",
    "_latency-90",
    "_workload",
    "_socket",
    "_diskio",
    "_error",
    "_mem",
    "_cpu",
]


def main():
    metrics_path = CASE_DIR / "metrics.parquet"
    logs_path = CASE_DIR / "logs.parquet"
    traces_path = CASE_DIR / "traces.parquet"

    for path in [metrics_path, logs_path, traces_path]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required dataset file not found: {path}"
            )

    metrics = pd.read_parquet(metrics_path)
    logs = pd.read_parquet(logs_path)
    traces = pd.read_parquet(traces_path)

    # Extract service names from metric column names.
    metric_services = set()

    for column in metrics.columns:
        for suffix in METRIC_SUFFIXES:
            if column.endswith(suffix):
                service = column[:-len(suffix)]
                metric_services.add(service)
                break

    log_containers = sorted(
        logs["container_name"].dropna().unique().tolist()
    )

    trace_services = sorted(
        traces["serviceName"].dropna().unique().tolist()
    )

    print("\n1. SERVICES IDENTIFIED IN METRICS")
    print("-" * 50)
    for service in sorted(metric_services):
        print(service)

    print(f"\nTotal metric services: {len(metric_services)}")

    print("\n2. CONTAINER NAMES IDENTIFIED IN LOGS")
    print("-" * 50)
    for container in log_containers:
        print(container)

    print(f"\nTotal distinct log containers: {len(log_containers)}")

    print("\n3. SERVICE NAMES IDENTIFIED IN TRACES")
    print("-" * 50)
    for service in trace_services:
        print(service)

    print(f"\nTotal distinct trace services: {len(trace_services)}")

    # Check exact matches only. Different names do not necessarily
    # mean different services; they may need mapping after inspection.
    print("\n4. EXACT NAME COMPARISON")
    print("-" * 50)

    metric_set = set(metric_services)
    trace_set = set(trace_services)
    log_set = set(log_containers)

    print("Services appearing in both metrics and traces:")
    print(sorted(metric_set & trace_set))

    print("\nMetric services with no exact trace-service match:")
    print(sorted(metric_set - trace_set))

    print("\nTrace services with no exact metric-service match:")
    print(sorted(trace_set - metric_set))

    print("\nLog container names matching metric services exactly:")
    print(sorted(metric_set & log_set))

    print("\nPROFILE COMPLETE")
    print("No source files were modified.")


if __name__ == "__main__":
    main()
