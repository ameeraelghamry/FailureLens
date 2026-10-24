
from pathlib import Path
from huggingface_hub import snapshot_download

# Find the FailureLens repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[4]

# Store the original benchmark files here.
RAW_DIR = (
    PROJECT_ROOT
    / "datasets"
    / "model B"
    / "raw"
    / "RCAEval"
)

# Download only this selected failure case.
CASE_ID = "re2tt_ts-order-service_delay_2"


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Dataset case: {CASE_ID}")
    print(f"Download location: {RAW_DIR}")
    print("Downloading the selected case only...")

    snapshot_download(
        repo_id="phamquiluan/RCAEval",
        repo_type="dataset",
        allow_patterns=[f"{CASE_ID}/*"],
        local_dir=str(RAW_DIR),
    )

    case_dir = RAW_DIR / CASE_ID

    print("\nDownload finished.")
    print(f"Case folder: {case_dir}")

    print("\nDownloaded files:")
    if case_dir.exists():
        for file_path in sorted(case_dir.iterdir()):
            print(f"  {file_path.name} ({file_path.stat().st_size:,} bytes)")
    else:
        print("WARNING: Expected case folder was not found.")
        print("Check the downloaded folder structure before continuing.")


if __name__ == "__main__":
    main()
