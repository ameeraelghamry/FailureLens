
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

PARQUET_FILES = ["metrics.parquet", "logs.parquet", "traces.parquet"]


def inspect_parquet(file_name):
    file_path = CASE_DIR / file_name

    print("\n" + "=" * 80)
    print(f"FILE: {file_name}")
    print("=" * 80)

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    df = pd.read_parquet(file_path)

    print(f"\nNumber of rows: {len(df):,}")
    print(f"Number of columns: {len(df.columns)}")

    print("\nColumn names:")
    for column in df.columns:
        print(f"  - {column}")

    print("\nColumn data types:")
    print(df.dtypes.to_string())

    print("\nMissing values (columns with missing data):")
    missing = df.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)

    if missing.empty:
        print("  No missing values detected.")
    else:
        for column, count in missing.head(15).items():
            percentage = count / len(df) * 100
            print(f"  {column}: {count:,} ({percentage:.2f}%)")

    print("\nFirst 2 records (preview):")
    with pd.option_context(
        "display.max_columns", 12,
        "display.max_colwidth", 80,
        "display.width", 160,
    ):
        print(df.head(2).to_string(index=False))


def main():
    if not CASE_DIR.exists():
        raise FileNotFoundError(f"Case folder not found: {CASE_DIR}")

    print(f"Inspecting case folder:\n{CASE_DIR}")

    for file_name in PARQUET_FILES:
        inspect_parquet(file_name)

    inject_time_path = CASE_DIR / "inject_time.txt"

    print("\n" + "=" * 80)
    print("FILE: inject_time.txt")
    print("=" * 80)

    if inject_time_path.exists():
        print("Raw timestamp content:")
        print(repr(inject_time_path.read_text(encoding="utf-8")))
    else:
        print("Injection timestamp file not found.")


if __name__ == "__main__":
    main()
