
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[4]

CASE_ID = "re2tt_ts-order-service_delay_2"

RAW_DIR = (
    PROJECT_ROOT / "datasets" / "model B" / "raw"
    / "RCAEval" / CASE_ID
)

PROCESSED_DIR = (
    PROJECT_ROOT / "datasets" / "model B" / "processed"
    / "RCAEval" / CASE_ID
)

REPORT_DIR = PROJECT_ROOT / "datasets" / "model B" / "reports"

METRIC_SUFFIXES = [
    "_latency-50",
    "_latency-90",
    "_workload",
    "_diskio",
    "_socket",
    "_error",
    "_mem",
    "_cpu",
]


def main():
    metrics = pd.read_parquet(RAW_DIR / "metrics.parquet")
    logs = pd.read_parquet(RAW_DIR / "logs.parquet")
    traces = pd.read_parquet(RAW_DIR / "traces.parquet")
    features = pd.read_parquet(
        PROCESSED_DIR / "service_features.parquet"
    )

    # Identify which metric types are actually present for each service.
    service_metric_types = {}

    for column in metrics.columns:
        for suffix in METRIC_SUFFIXES:
            if column.endswith(suffix):
                service = column[:-len(suffix)]
                metric_type = suffix.lstrip("_")

                service_metric_types.setdefault(
                    service, set()
                ).add(metric_type)
                break

    log_services = set(
        logs["container_name"].dropna().unique()
    )
    trace_services = set(
        traces["serviceName"].dropna().unique()
    )

    rows = []

    for service in sorted(features["service"].unique()):
        available_types = service_metric_types.get(service, set())

        row = {
            "service": service,
            "has_metrics": service in service_metric_types,
            "has_logs": service in log_services,
            "has_traces": service in trace_services,
            "metric_type_count": len(available_types),
        }

        for metric_type in [
            "cpu", "mem", "error", "socket",
            "diskio", "workload", "latency-50", "latency-90"
        ]:
            row[f"has_{metric_type}"] = (
                metric_type in available_types
            )

        rows.append(row)

    coverage = pd.DataFrame(rows)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORT_DIR / "case_evidence_coverage.csv"
    coverage.to_csv(output_path, index=False)

    print("\nEVIDENCE COVERAGE REPORT")
    print("=" * 55)
    print(f"Services checked: {len(coverage)}")

    print("\n1. SERVICES WITH EACH EVIDENCE SOURCE")
    print("-" * 55)

    for source in ["has_metrics", "has_logs", "has_traces"]:
        print(f"{source}: {int(coverage[source].sum())}")

    print("\n2. SERVICES WITH EACH METRIC TYPE")
    print("-" * 55)

    metric_columns = [
        col for col in coverage.columns
        if col.startswith("has_")
        and col not in ["has_metrics", "has_logs", "has_traces"]
    ]

    for column in metric_columns:
        print(f"{column}: {int(coverage[column].sum())}")

    print("\n3. OVERLAP BETWEEN EVIDENCE SOURCES")
    print("-" * 55)

    print(
        "Services with metrics AND logs AND traces:",
        int(
            (
                coverage["has_metrics"]
                & coverage["has_logs"]
                & coverage["has_traces"]
            ).sum()
        ),
    )

    print(
        "Services with metrics but no traces:",
        int(
            (
                coverage["has_metrics"]
                & ~coverage["has_traces"]
            ).sum()
        ),
    )

    print(
        "Services with logs but no traces:",
        int(
            (
                coverage["has_logs"]
                & ~coverage["has_traces"]
            ).sum()
        ),
    )

    print("\n4. SERVICES WITHOUT TRACE COVERAGE")
    print("-" * 55)

    print(
        coverage.loc[
            ~coverage["has_traces"], "service"
        ].to_string(index=False)
    )

    print("\n5. OUTPUT")
    print("-" * 55)
    print(f"Saved: {output_path}")
    print("Raw and processed source files were not modified.")


if __name__ == "__main__":
    main()
