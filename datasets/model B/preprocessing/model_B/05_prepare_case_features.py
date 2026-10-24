from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

CASE_ID = "re2tt_ts-order-service_delay_2"

PROJECT_ROOT = Path(__file__).resolve().parents[4]

RAW_CASE_DIR = (
    PROJECT_ROOT
    / "datasets"
    / "model B"
    / "raw"
    / "RCAEval"
    / CASE_ID
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "datasets"
    / "model B"
    / "processed"
    / "RCAEval"
    / CASE_ID
)

INDEX_PATH = (
    PROJECT_ROOT
    / "datasets"
    / "model B"
    / "raw"
    / "RCAEval"
    / "cases.parquet"
)

METRICS_FILE = RAW_CASE_DIR / "metrics.parquet"
LOGS_FILE = RAW_CASE_DIR / "logs.parquet"
TRACES_FILE = RAW_CASE_DIR / "traces.parquet"
INJECT_TIME_FILE = RAW_CASE_DIR / "inject_time.txt"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def require_file(path: Path) -> None:
    """Stop with a clear message if a required file is missing."""
    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: {path}"
        )


def get_metric_service_and_type(column_name: str):
    """
    Split a metric column name into its service name and metric type.

    Example:
        ts-order-service_cpu
        -> ("ts-order-service", "cpu")

    Uses the final underscore to separate the metric type,
    preserving underscores that may occur in service names.
    """
    if "_" not in column_name:
        return None, None

    service, metric_type = column_name.rsplit("_", 1)

    return service, metric_type


def safe_mean(series: pd.Series):
    """Calculate a mean while ignoring missing values."""
    values = pd.to_numeric(series, errors="coerce").dropna()

    if values.empty:
        return np.nan

    return float(values.mean())


def safe_std(series: pd.Series):
    """Calculate standard deviation while ignoring missing values."""
    values = pd.to_numeric(series, errors="coerce").dropna()

    if len(values) < 2:
        return np.nan

    return float(values.std())


def safe_max(series: pd.Series):
    """Calculate a maximum while ignoring missing values."""
    values = pd.to_numeric(series, errors="coerce").dropna()

    if values.empty:
        return np.nan

    return float(values.max())


def safe_missing_fraction(series: pd.Series):
    """Calculate the fraction of values that are missing."""
    if len(series) == 0:
        return np.nan

    return float(series.isna().mean())


def add_metric_features(
    row: dict,
    service: str,
    metric_type: str,
    metric_column: str,
    metrics: pd.DataFrame,
    pre_mask: pd.Series,
    post_mask: pd.Series,
) -> None:
    """
    Add pre-injection and post-injection statistics for one metric.

    The injection timestamp separates the two periods.
    These features support retrospective root-cause analysis.
    """

    pre_values = metrics.loc[pre_mask, metric_column]
    post_values = metrics.loc[post_mask, metric_column]

    pre_mean = safe_mean(pre_values)
    post_mean = safe_mean(post_values)

    row[f"has_{metric_type}"] = 1

    row[f"metric_{metric_type}_pre_mean"] = pre_mean
    row[f"metric_{metric_type}_pre_std"] = safe_std(pre_values)
    row[f"metric_{metric_type}_pre_max"] = safe_max(pre_values)
    row[f"metric_{metric_type}_pre_missing_fraction"] = (
        safe_missing_fraction(pre_values)
    )

    row[f"metric_{metric_type}_post_mean"] = post_mean
    row[f"metric_{metric_type}_post_std"] = safe_std(post_values)
    row[f"metric_{metric_type}_post_max"] = safe_max(post_values)
    row[f"metric_{metric_type}_post_missing_fraction"] = (
        safe_missing_fraction(post_values)
    )

    if pd.notna(pre_mean) and pd.notna(post_mean):
        row[f"metric_{metric_type}_mean_delta"] = (
            post_mean - pre_mean
        )
    else:
        row[f"metric_{metric_type}_mean_delta"] = np.nan


def add_unavailable_metric_flags(row: dict) -> None:
    """
    Add explicit flags for expected metric types that are unavailable
    for a particular service.

    Missing metric values are not automatically replaced with zero.
    """
    expected_metric_types = [
        "cpu",
        "mem",
        "diskio",
        "socket",
        "workload",
        "error",
        "latency-50",
        "latency-90",
    ]

    for metric_type in expected_metric_types:
        flag_name = f"has_{metric_type}"

        if flag_name not in row:
            row[flag_name] = 0


# ============================================================
# MAIN FEATURE PREPARATION
# ============================================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # 1. Check that the required files exist
    # --------------------------------------------------------

    for path in [
        INDEX_PATH,
        METRICS_FILE,
        LOGS_FILE,
        TRACES_FILE,
        INJECT_TIME_FILE,
    ]:
        require_file(path)

    # --------------------------------------------------------
    # 2. Read the benchmark metadata and retrieve the label
    # --------------------------------------------------------

    case_index = pd.read_parquet(INDEX_PATH)

    matching_cases = case_index[
        case_index["case"] == CASE_ID
    ]

    if len(matching_cases) != 1:
        raise ValueError(
            f"Expected exactly one metadata row for {CASE_ID}, "
            f"but found {len(matching_cases)}."
        )

    root_cause_service = matching_cases.iloc[0][
        "root_cause_service"
    ]

    if (
        pd.isna(root_cause_service)
        or not str(root_cause_service).strip()
    ):
        raise ValueError(
            f"Missing root-cause service label for {CASE_ID}."
        )

    root_cause_service = str(root_cause_service).strip()

    print(f"Case ID: {CASE_ID}")
    print(
        "Benchmark root-cause service:",
        root_cause_service,
    )

    # --------------------------------------------------------
    # 3. Load the raw evidence files
    # --------------------------------------------------------

    metrics = pd.read_parquet(METRICS_FILE)
    logs = pd.read_parquet(LOGS_FILE)
    traces = pd.read_parquet(TRACES_FILE)

    inject_time = float(
        INJECT_TIME_FILE.read_text(
            encoding="utf-8"
        ).strip()
    )

    print("\nRAW DATA SIZES")
    print(f"Metrics: {len(metrics):,} rows")
    print(f"Logs:    {len(logs):,} rows")
    print(f"Traces:  {len(traces):,} rows")
    print(f"Injection timestamp: {inject_time}")

    # --------------------------------------------------------
    # 4. Validate timestamp columns
    # --------------------------------------------------------

    if "time" not in metrics.columns:
        raise ValueError(
            "Metrics file must contain a 'time' column."
        )

    if "timestamp" not in logs.columns:
        raise ValueError(
            "Logs file must contain a 'timestamp' column."
        )

    if "container_name" not in logs.columns:
        raise ValueError(
            "Logs file must contain a 'container_name' column."
        )

    if "startTimeMillis" not in traces.columns:
        raise ValueError(
            "Traces file must contain a 'startTimeMillis' column."
        )

    if "serviceName" not in traces.columns:
        raise ValueError(
            "Traces file must contain a 'serviceName' column."
        )

    # Convert timestamp fields to numeric values.
    metrics["time"] = pd.to_numeric(
        metrics["time"],
        errors="coerce",
    )

    logs["timestamp"] = pd.to_numeric(
        logs["timestamp"],
        errors="coerce",
    )

    traces["startTimeMillis"] = pd.to_numeric(
        traces["startTimeMillis"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # 5. Split evidence into pre-injection and post-injection
    # --------------------------------------------------------

    # Metrics and logs use Unix timestamps in seconds.
    metrics_pre_mask = metrics["time"] < inject_time
    metrics_post_mask = metrics["time"] >= inject_time

    logs_pre_mask = logs["timestamp"] < inject_time
    logs_post_mask = logs["timestamp"] >= inject_time

    # Trace timestamps use Unix epoch milliseconds.
    inject_time_millis = inject_time * 1000

    traces_pre_mask = (
        traces["startTimeMillis"] < inject_time_millis
    )

    traces_post_mask = (
        traces["startTimeMillis"] >= inject_time_millis
    )

    print("\nTIMELINE COUNTS")
    print(
        "Metrics before injection:",
        int(metrics_pre_mask.sum()),
    )
    print(
        "Metrics at/after injection:",
        int(metrics_post_mask.sum()),
    )
    print(
        "Logs before injection:",
        int(logs_pre_mask.sum()),
    )
    print(
        "Logs at/after injection:",
        int(logs_post_mask.sum()),
    )
    print(
        "Traces before injection:",
        int(traces_pre_mask.sum()),
    )
    print(
        "Traces at/after injection:",
        int(traces_post_mask.sum()),
    )

    # --------------------------------------------------------
    # 6. Identify services represented in the evidence
    # --------------------------------------------------------

    metric_columns = [
        column
        for column in metrics.columns
        if column != "time"
    ]

    metric_service_columns = {}

    for column in metric_columns:
        service, metric_type = get_metric_service_and_type(
            column
        )

        if service is None or metric_type is None:
            continue

        metric_service_columns.setdefault(
            service, {}
        )[metric_type] = column

    metric_services = set(metric_service_columns.keys())

    log_services = set(
        logs["container_name"]
        .dropna()
        .astype(str)
        .unique()
    )

    trace_services = set(
        traces["serviceName"]
        .dropna()
        .astype(str)
        .unique()
    )

    # The feature table contains services observed in at least
    # one of the three evidence sources.
    services = sorted(
        metric_services
        | log_services
        | trace_services
    )

    if not services:
        raise ValueError(
            f"No services found in evidence for {CASE_ID}."
        )

    print("\nSERVICE COUNTS")
    print(f"Metric services: {len(metric_services)}")
    print(f"Log services:    {len(log_services)}")
    print(f"Trace services:  {len(trace_services)}")
    print(f"Combined services: {len(services)}")

    if root_cause_service not in services:
        raise ValueError(
            "The benchmark root-cause service "
            f"'{root_cause_service}' does not appear in the "
            "combined evidence service list. Check service-name "
            "mapping before continuing."
        )

    # --------------------------------------------------------
    # 7. Prepare lookup tables for log and trace counts
    # --------------------------------------------------------

    logs_pre_counts = (
        logs.loc[logs_pre_mask]
        .groupby("container_name")
        .size()
        .to_dict()
    )

    logs_post_counts = (
        logs.loc[logs_post_mask]
        .groupby("container_name")
        .size()
        .to_dict()
    )

    traces_pre_counts = (
        traces.loc[traces_pre_mask]
        .groupby("serviceName")
        .size()
        .to_dict()
    )

    traces_post_counts = (
        traces.loc[traces_post_mask]
        .groupby("serviceName")
        .size()
        .to_dict()
    )

    # --------------------------------------------------------
    # 8. Calculate service-level features
    # --------------------------------------------------------

    feature_rows = []

    for service in services:
        row = {
            "case_id": CASE_ID,
            "service": service,
        }

        # ....................................................
        # A. Evidence availability flags
        # ....................................................

        row["has_metrics"] = int(
            service in metric_services
        )

        row["has_logs"] = int(
            service in log_services
        )

        row["has_traces"] = int(
            service in trace_services
        )

        row["has_logs_pre"] = int(
            logs_pre_counts.get(service, 0) > 0
        )

        row["has_logs_post"] = int(
            logs_post_counts.get(service, 0) > 0
        )

        row["has_traces_pre"] = int(
            traces_pre_counts.get(service, 0) > 0
        )

        row["has_traces_post"] = int(
            traces_post_counts.get(service, 0) > 0
        )

        # ....................................................
        # B. Log and trace record counts
        # ....................................................

        row["log_count_pre"] = int(
            logs_pre_counts.get(service, 0)
        )

        row["log_count_post"] = int(
            logs_post_counts.get(service, 0)
        )

        row["trace_count_pre"] = int(
            traces_pre_counts.get(service, 0)
        )

        row["trace_count_post"] = int(
            traces_post_counts.get(service, 0)
        )

        # ....................................................
        # C. Metric features
        # ....................................................

        available_metrics = metric_service_columns.get(
            service, {}
        )

        for metric_type, metric_column in available_metrics.items():
            add_metric_features(
                row=row,
                service=service,
                metric_type=metric_type,
                metric_column=metric_column,
                metrics=metrics,
                pre_mask=metrics_pre_mask,
                post_mask=metrics_post_mask,
            )

        add_unavailable_metric_flags(row)

        # ....................................................
        # D. Trace-duration features
        # ....................................................

        if service in trace_services:
            service_traces = traces[
                traces["serviceName"].astype(str) == service
            ]

            # Convert duration to numeric where possible.
            if "duration" in service_traces.columns:
                durations = pd.to_numeric(
                    service_traces["duration"],
                    errors="coerce",
                )

                pre_durations = durations.loc[
                    traces_pre_mask.loc[
                        service_traces.index
                    ]
                ]

                post_durations = durations.loc[
                    traces_post_mask.loc[
                        service_traces.index
                    ]
                ]

                row["trace_duration_pre_mean"] = safe_mean(
                    pre_durations
                )

                row["trace_duration_pre_std"] = safe_std(
                    pre_durations
                )

                row["trace_duration_pre_max"] = safe_max(
                    pre_durations
                )

                row[
                    "trace_duration_pre_missing_fraction"
                ] = safe_missing_fraction(pre_durations)

                row["trace_duration_post_mean"] = safe_mean(
                    post_durations
                )

                row["trace_duration_post_std"] = safe_std(
                    post_durations
                )

                row["trace_duration_post_max"] = safe_max(
                    post_durations
                )

                row[
                    "trace_duration_post_missing_fraction"
                ] = safe_missing_fraction(post_durations)

                pre_duration_mean = row[
                    "trace_duration_pre_mean"
                ]

                post_duration_mean = row[
                    "trace_duration_post_mean"
                ]

                if (
                    pd.notna(pre_duration_mean)
                    and pd.notna(post_duration_mean)
                ):
                    row["trace_duration_mean_delta"] = (
                        post_duration_mean
                        - pre_duration_mean
                    )
                else:
                    row["trace_duration_mean_delta"] = np.nan

            else:
                row["trace_duration_pre_mean"] = np.nan
                row["trace_duration_pre_std"] = np.nan
                row["trace_duration_pre_max"] = np.nan
                row[
                    "trace_duration_pre_missing_fraction"
                ] = np.nan

                row["trace_duration_post_mean"] = np.nan
                row["trace_duration_post_std"] = np.nan
                row["trace_duration_post_max"] = np.nan
                row[
                    "trace_duration_post_missing_fraction"
                ] = np.nan

                row["trace_duration_mean_delta"] = np.nan

        else:
            row["trace_duration_pre_mean"] = np.nan
            row["trace_duration_pre_std"] = np.nan
            row["trace_duration_pre_max"] = np.nan
            row[
                "trace_duration_pre_missing_fraction"
            ] = np.nan

            row["trace_duration_post_mean"] = np.nan
            row["trace_duration_post_std"] = np.nan
            row["trace_duration_post_max"] = np.nan
            row[
                "trace_duration_post_missing_fraction"
            ] = np.nan

            row["trace_duration_mean_delta"] = np.nan

        # ....................................................
        # E. Benchmark target label
        # ....................................................

        # This is the ground-truth target for evaluation.
        # Do not include it among model input features.
        row["is_root_cause"] = int(
            service == root_cause_service
        )

        feature_rows.append(row)

    # --------------------------------------------------------
    # 9. Build the final feature table
    # --------------------------------------------------------

    features = pd.DataFrame(feature_rows)

    # Make sure indicator columns are integer-valued.
    flag_columns = [
        column
        for column in features.columns
        if column.startswith("has_")
    ]

    for column in flag_columns:
        features[column] = features[column].fillna(0).astype(int)

    features["is_root_cause"] = (
        features["is_root_cause"].astype(int)
    )

    # --------------------------------------------------------
    # 10. Basic checks before saving
    # --------------------------------------------------------

    if features["service"].duplicated().any():
        duplicate_services = features.loc[
            features["service"].duplicated(),
            "service",
        ].tolist()

        raise ValueError(
            f"Duplicate service rows found: {duplicate_services}"
        )

    positive_labels = int(
        features["is_root_cause"].sum()
    )

    if positive_labels != 1:
        raise ValueError(
            "Expected exactly one root-cause service label "
            f"for this case, but found {positive_labels}."
        )

    if not features["is_root_cause"].isin([0, 1]).all():
        raise ValueError(
            "'is_root_cause' must contain only 0 or 1."
        )

    # --------------------------------------------------------
    # 11. Save the processed feature table
    # --------------------------------------------------------

    csv_path = OUTPUT_DIR / "service_features.csv"
    parquet_path = OUTPUT_DIR / "service_features.parquet"

    features.to_csv(
        csv_path,
        index=False,
    )

    features.to_parquet(
        parquet_path,
        index=False,
    )

    # --------------------------------------------------------
    # 12. Print a summary
    # --------------------------------------------------------

    print("\nFEATURE TABLE CREATED SUCCESSFULLY")
    print(f"Case: {CASE_ID}")
    print(f"Root-cause service: {root_cause_service}")
    print(f"Services: {len(features)}")
    print(f"Columns: {len(features.columns)}")
    print(f"Root-cause label matches: {positive_labels}")

    print("\nEVIDENCE COVERAGE")

    for column in [
        "has_metrics",
        "has_logs",
        "has_traces",
        "has_logs_pre",
        "has_logs_post",
        "has_traces_pre",
        "has_traces_post",
    ]:
        print(
            f"{column}: {int(features[column].sum())}"
        )

    print("\nMETRIC AVAILABILITY")

    metric_flag_columns = sorted(
        column
        for column in features.columns
        if column.startswith("has_")
        and column not in {
            "has_metrics",
            "has_logs",
            "has_traces",
            "has_logs_pre",
            "has_logs_post",
            "has_traces_pre",
            "has_traces_post",
        }
    )

    for column in metric_flag_columns:
        print(
            f"{column}: {int(features[column].sum())}"
        )

    print("\nSAVED FILES")
    print(csv_path)
    print(parquet_path)


if __name__ == "__main__":
    main()