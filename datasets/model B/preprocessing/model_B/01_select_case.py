from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[4]
INDEX_PATH = (
    PROJECT_ROOT
    / "datasets"
    / "model B"
    / "raw"
    / "RCAEval"
    / "cases.parquet"
)


def main():
    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"Dataset index not found: {INDEX_PATH}"
        )

    df = pd.read_parquet(INDEX_PATH)

    # Keep cases that have both logs and traces.
    re2 = df[
        (df["suite"] == "RE2")
        & (df["has_logs"])
        & (df["has_traces"])
    ].copy()

    # Rank cases by the combined number of log and trace records.
    re2["combined_records"] = (
        re2["n_logs"] + re2["n_traces"]
    )

    candidates = re2.sort_values("combined_records")

    columns = [
        "case",
        "dataset",
        "root_cause_service",
        "fault",
        "n_metrics",
        "n_logs",
        "n_traces",
        "combined_records",
    ]

    print(f"RE2 cases with logs and traces: {len(re2)}")
    print("\n10 cases with the smallest combined record counts:\n")
    print(candidates[columns].head(10).to_string(index=False))


if __name__ == "__main__":
    main()