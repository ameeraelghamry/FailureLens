from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[4]
INDEX_PATH = PROJECT_ROOT / "datasets" / "model B" / "raw" / "RCAEval" / "cases.parquet"

INDEX_URL = "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/main/cases.parquet"


def main():
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not INDEX_PATH.exists():
        print("Downloading the RCAEval case index...")
        pd.read_parquet(INDEX_URL).to_parquet(INDEX_PATH, index=False)

    df = pd.read_parquet(INDEX_PATH)

    print("\nDataset index loaded successfully.")
    print(f"Number of cases: {len(df)}")

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nFirst five records:")
    print(df.head().to_string())

    print("\nAvailable datasets:")
    if "dataset" in df.columns:
        print(df["dataset"].value_counts().to_string())


if __name__ == "__main__":
    main()