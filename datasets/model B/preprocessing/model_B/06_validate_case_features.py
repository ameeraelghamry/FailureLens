
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA_PATH = (
    PROJECT_ROOT
    / "datasets"
    / "model B"
    / "processed"
    / "RCAEval"
    / "re2tt_ts-order-service_delay_2"
    / "service_features.parquet"
)

REPORT_DIR = (
    PROJECT_ROOT
    / "datasets"
    / "model B"
    / "reports"
)

LABEL_COLUMN = "is_root_cause"
IDENTIFIER_COLUMNS = ["case_id", "service", LABEL_COLUMN]


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Processed dataset not found: {DATA_PATH}"
        )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(DATA_PATH)
    lines = []

    def report(message=""):
        print(message)
        lines.append(message)

    report("MODEL B PROCESSED DATA VALIDATION")
    report("=" * 55)
    report(f"Dataset: {DATA_PATH}")
    report(f"Rows: {len(df)}")
    report(f"Columns: {len(df.columns)}")

    report("\n1. REQUIRED COLUMNS")
    report("-" * 55)

    required = ["case_id", "service", LABEL_COLUMN]
    missing_required = [
        col for col in required if col not in df.columns
    ]

    if missing_required:
        report(f"FAIL: Missing columns: {missing_required}")
    else:
        report("PASS: All required columns exist.")

    report("\n2. DUPLICATE SERVICE ROWS")
    report("-" * 55)

    if "service" in df.columns:
        duplicate_count = int(df["service"].duplicated().sum())
        report(f"Duplicate service rows: {duplicate_count}")
    else:
        duplicate_count = None
        report("Cannot check: service column is missing.")

    report("\n3. ROOT-CAUSE LABEL")
    report("-" * 55)

    if LABEL_COLUMN in df.columns:
        report("Label counts:")
        report(df[LABEL_COLUMN].value_counts(
            dropna=False
        ).to_string())

        positive_count = int((df[LABEL_COLUMN] == 1).sum())
        report(f"Positive root-cause rows: {positive_count}")
    else:
        report("Cannot check: label column is missing.")

    report("\n4. MISSING VALUES")
    report("-" * 55)

    missing_counts = df.isna().sum()
    missing_counts = missing_counts[
        missing_counts > 0
    ].sort_values(ascending=False)

    if missing_counts.empty:
        report("No missing values.")
    else:
        report("Columns with missing values:")
        report(missing_counts.head(20).to_string())

    report("\n5. INFINITE NUMERIC VALUES")
    report("-" * 55)

    numeric_df = df.select_dtypes(include="number")
    infinite_counts = {}

    for column in numeric_df.columns:
        count = int(np.isinf(numeric_df[column]).sum())
        if count > 0:
            infinite_counts[column] = count

    if infinite_counts:
        report(pd.Series(infinite_counts).to_string())
    else:
        report("No infinite numeric values found.")

    report("\n6. MODEL INPUTS VS. LABEL")
    report("-" * 55)

    input_columns = [
        col for col in df.columns
        if col not in IDENTIFIER_COLUMNS
    ]

    report(f"Potential input feature columns: {len(input_columns)}")
    report(f"Target label column: {LABEL_COLUMN}")
    report("The target label must never be included as an input feature.")
    report("Case ID and service name are identifiers, not numeric evidence.")

    suspicious = [
        col for col in input_columns
        if "root_cause" in col.lower()
        or col.lower() in ["fault", "fault_type", "label", "target"]
    ]

    if suspicious:
        report(f"Review these potentially leaking columns: {suspicious}")
    else:
        report("No obvious target-label columns found among potential inputs.")

    report("\n7. VALIDATION SUMMARY")
    report("-" * 55)

    if missing_required:
        report("STATUS: FAIL — required columns are missing.")
    elif len(df) == 0:
        report("STATUS: FAIL — dataset is empty.")
    elif duplicate_count and duplicate_count > 0:
        report("STATUS: REVIEW — duplicate service rows exist.")
    elif LABEL_COLUMN in df.columns and positive_count != 1:
        report("STATUS: REVIEW — expected one positive service label.")
    else:
        report("STATUS: STRUCTURAL CHECKS PASSED.")
        report("Missing values still require documented handling.")
        report("This single case is not sufficient for model training.")

    report("\nValidation finished. The dataset was not modified.")

    report_path = REPORT_DIR / "case_feature_validation.txt"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
