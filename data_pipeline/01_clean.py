"""
INPUT:
    data/raw/Jee_Neet_subjectsquestions.csv
    Columns: eng (question text), Subject

OUTPUT:
    data/processed/cleaned.csv
    data/processed/quarantined.csv
    data/reports/cleaning_report.json
"""

import os
import re
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd

MIN_QUESTION_LENGTH = 15

# Maximum character length. Questions above this are flagged (not removed)
MAX_QUESTION_LENGTH = 5000

# Valid subject values. Any row with a subject outside this set is quarantined.
VALID_SUBJECTS = {"Biology", "Chemistry", "Maths", "Physics"}

# These patterns indicate OCR or scraping artifacts, not real questions.
CORRUPTION_PATTERNS = [
    r"^tood",           # Known corrupt prefix found in dataset inspection
    r"^[0-9\s\n]+$",   # Rows that are purely numbers and whitespace — no text
    r"^[\W\s]+$",       # Rows with only non-word characters
]

# LOGGING SETUP
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# PATH RESOLUTION
def resolve_paths(input_csv: str) -> dict:
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    paths = {
        "input":       Path(input_csv) if os.path.isabs(input_csv)
                       else project_root / input_csv,
        "cleaned":     script_dir / "data" / "processed" / "cleaned.csv",
        "quarantined": script_dir / "data" / "processed" / "quarantined.csv",
        "report":      script_dir / "data" / "reports" / "cleaning_report.json",
    }

    # Create output directories
    paths["cleaned"].parent.mkdir(parents=True, exist_ok=True)
    paths["report"].parent.mkdir(parents=True, exist_ok=True)

    return paths

# STEP 1: LOAD DATA

def load_raw_data(input_path: Path) -> pd.DataFrame:
    logger.info(f"Loading raw dataset from: {input_path}")

    df = pd.read_csv(
        input_path,
        encoding="utf-8",
        encoding_errors="replace",  # Replace undecodable bytes with ?
        dtype=str,                  # Load all columns as string — no type coercion
        keep_default_na=False,      # Do not auto-convert empty strings to NaN yet
    )

    logger.info(f"Raw dataset loaded: {len(df):,} rows, {len(df.columns)} columns")
    logger.info(f"Columns found: {df.columns.tolist()}")

    # Validate expected columns exist
    required_columns = {"eng", "Subject"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(
            f"CRITICAL: Missing required columns: {missing}. "
            f"Found columns: {df.columns.tolist()}"
        )

    return df

# STEP 2: VALIDATE AND FLAG ISSUES
def flag_issues(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Running issue detection across all rows...")

    # Add tracking columns
    df = df.copy()
    df["quarantine_reason"] = ""
    df["original_row_index"] = df.index

    issues_found = {
        "empty_text":       0,
        "invalid_subject":  0,
        "too_short":        0,
        "too_long":         0,
        "corruption":       0,
        "whitespace_only":  0,
    }

    # 2a. Empty or NaN text 
    empty_mask = df["eng"].isna() | (df["eng"].str.strip() == "")
    df.loc[empty_mask, "quarantine_reason"] += "empty_text|"
    issues_found["empty_text"] = empty_mask.sum()

    # 2b. Invalid subject 
    invalid_subj_mask = ~df["Subject"].isin(VALID_SUBJECTS)
    df.loc[invalid_subj_mask, "quarantine_reason"] += "invalid_subject|"
    issues_found["invalid_subject"] = invalid_subj_mask.sum()

    # 2c. Text too short 
    # We fill NaN temporarily to avoid length errors on empty rows
    lengths = df["eng"].fillna("").str.len()
    too_short_mask = lengths < MIN_QUESTION_LENGTH
    df.loc[too_short_mask, "quarantine_reason"] += "too_short|"
    issues_found["too_short"] = too_short_mask.sum()

    # 2d. Text too long (flag only, may be valid complex problem) 
    too_long_mask = lengths > MAX_QUESTION_LENGTH
    df.loc[too_long_mask, "quarantine_reason"] += "too_long_flagged|"
    issues_found["too_long"] = too_long_mask.sum()

    # 2e. Corruption patterns 
    for pattern in CORRUPTION_PATTERNS:
        try:
            corrupt_mask = df["eng"].fillna("").str.match(pattern, case=False)
            df.loc[corrupt_mask, "quarantine_reason"] += f"corruption_pattern|"
            issues_found["corruption"] += corrupt_mask.sum()
        except re.error:
            logger.warning(f"Invalid regex pattern skipped: {pattern}")

    # 2f. Whitespace only text 
    whitespace_mask = df["eng"].fillna("").str.strip().str.len() == 0
    df.loc[whitespace_mask & (df["quarantine_reason"] == ""), "quarantine_reason"] += "whitespace_only|"
    issues_found["whitespace_only"] = whitespace_mask.sum()

    # Cleaning the pipe from reason strings
    df["quarantine_reason"] = df["quarantine_reason"].str.rstrip("|")

    total_flagged = (df["quarantine_reason"] != "").sum()
    logger.info(f"Issue detection complete. Rows flagged: {total_flagged:,}")
    for issue, count in issues_found.items():
        if count > 0:
            logger.info(f"  {issue}: {count:,} rows")

    return df, issues_found


# STEP 3: NORMALIZE TEXT (SAFE — MATH-PRESERVING)
def normalize_text(text: str) -> str:
    """
    WHAT WE DO:
        - Normalize Windows line endings (\\r\\n → \\n)
        - End sequences of 3+ blank lines into 2 (preserve paragraph structure)
    """
    if not isinstance(text, str):
        return text

    # Normalize Windows line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize Unicode whitespace (non-breaking space -> regular space)
    text = text.replace("\u00a0", " ").replace("\u200b", "")

    # Strip leading/trailing whitespace
    text = text.strip()

    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Normalize multiple spaces within a line to single space
    lines = text.split("\n")
    lines = [re.sub(r" {2,}", " ", line) for line in lines]
    text = "\n".join(lines)

    return text


def apply_normalization(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Applying text normalization to valid rows...")

    # Only normalize rows that are NOT quarantined
    valid_mask = df["quarantine_reason"] == ""
    df.loc[valid_mask, "eng"] = df.loc[valid_mask, "eng"].apply(normalize_text)
    df["Subject"] = df["Subject"].str.strip()

    logger.info(f"Normalization applied to {valid_mask.sum():,} valid rows")
    return df

# STEP 4: REMOVE EXACT DUPLICATES
def remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    logger.info("Detecting exact duplicates...")

    # Only check duplicates among rows that are not been quarantined
    valid_mask = df["quarantine_reason"] == ""
    valid_df = df[valid_mask].copy()

    # Identify duplicates among valid rows only
    is_duplicate = valid_df.duplicated(subset=["eng"], keep="first")
    duplicate_indices = valid_df[is_duplicate].index

    df.loc[duplicate_indices, "quarantine_reason"] = "exact_duplicate"

    dupe_count = len(duplicate_indices)
    logger.info(f"Duplicate rows quarantined: {dupe_count:,}")

    return df, dupe_count

# STEP 5: SPLIT AND SAVE
def split_and_save(df: pd.DataFrame, paths: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split into cleaned and quarantined DataFrames, then save both.
    """
    cleaned = df[df["quarantine_reason"] == ""].copy()
    quarantined = df[df["quarantine_reason"] != ""].copy()

    # Remove internal tracking columns from cleaned output
    cleaned = cleaned.drop(columns=["quarantine_reason", "original_row_index"])

    # Add a clean sequential index to cleaned output
    cleaned = cleaned.reset_index(drop=True)
    cleaned.insert(0, "row_id", cleaned.index)  # row_id = 0-indexed clean row number

    # Save cleaned
    cleaned.to_csv(paths["cleaned"], index=False, encoding="utf-8")
    logger.info(f"Cleaned dataset saved: {len(cleaned):,} rows → {paths['cleaned']}")

    # Save quarantined (with original index for traceability)
    quarantined.to_csv(paths["quarantined"], index=False, encoding="utf-8")
    logger.info(f"Quarantined rows saved: {len(quarantined):,} rows → {paths['quarantined']}")

    return cleaned, quarantined



# STEP 6: GENERATE AUDIT REPORT
def generate_report(
    raw_count: int,
    cleaned: pd.DataFrame,
    quarantined: pd.DataFrame,
    issues_found: dict,
    dupe_count: int,
    paths: dict,
    start_time: datetime,
) -> dict:
    end_time = datetime.now()
    duration_seconds = (end_time - start_time).total_seconds()

    # Quarantine breakdown by reason
    quarantine_breakdown = {}
    if len(quarantined) > 0:
        for _, row in quarantined.iterrows():
            reasons = row["quarantine_reason"].split("|")
            for reason in reasons:
                reason = reason.strip()
                if reason:
                    quarantine_breakdown[reason] = quarantine_breakdown.get(reason, 0) + 1

    # Subject distribution in cleaned data
    subject_distribution = cleaned["Subject"].value_counts().to_dict()

    # Question length statistics in cleaned data
    lengths = cleaned["eng"].str.len()
    length_stats = {
        "min":    int(lengths.min()),
        "max":    int(lengths.max()),
        "mean":   round(float(lengths.mean()), 2),
        "median": round(float(lengths.median()), 2),
        "std":    round(float(lengths.std()), 2),
    }

    # LATEX presence in cleaned data
    latex_count = cleaned["eng"].str.contains(
        r"\\frac|\\sqrt|\\alpha|\\theta|\\beta|\\omega",
        regex=True, na=False
    ).sum()

    # MCQ options presence
    mcq_count = cleaned["eng"].str.contains("\nA.", regex=False, na=False).sum()

    report = {
        "pipeline_step": "01_clean.py",
        "timestamp": end_time.isoformat(),
        "duration_seconds": round(duration_seconds, 2),
        "data_summary": {
            "raw_rows":           raw_count,
            "cleaned_rows":       len(cleaned),
            "quarantined_rows":   len(quarantined),
            "retention_rate_pct": round(len(cleaned) / raw_count * 100, 2),
        },
        "issues_detected": {
            **issues_found,
            "exact_duplicates": dupe_count,
        },
        "quarantine_breakdown_by_reason": quarantine_breakdown,
        "cleaned_dataset_stats": {
            "subject_distribution":   subject_distribution,
            "question_length":        length_stats,
            "rows_with_latex":        int(latex_count),
            "latex_pct":              round(int(latex_count) / len(cleaned) * 100, 2),
            "rows_with_mcq_options":  int(mcq_count),
            "mcq_pct":                round(int(mcq_count) / len(cleaned) * 100, 2),
        },
        "output_paths": {
            "cleaned":     str(paths["cleaned"]),
            "quarantined": str(paths["quarantined"]),
            "report":      str(paths["report"]),
        },
    }

    # Custom encoder to handle numpy int64 / float64 types from pandas
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            import numpy as np
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    with open(paths["report"], "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, cls=NumpyEncoder)

    logger.info(f"Audit report saved: {paths['report']}")
    return report

# PIPELINE ORCHESTRATOR
def run_cleaning_pipeline(input_csv: str) -> dict:
    
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("01_clean.py — Starting Data Cleaning Pipeline")
    logger.info("=" * 60)

    # Resolve paths
    paths = resolve_paths(input_csv)

    # Step 1: Load
    df = load_raw_data(paths["input"])
    raw_count = len(df)

    # Step 2: Flag issues
    df, issues_found = flag_issues(df)

    # Step 3: Normalize text (only on valid rows)
    df = apply_normalization(df)

    # Step 4: Remove duplicates (only in currently valid rows)
    df, dupe_count = remove_duplicates(df)

    # Step 5: Split and save
    cleaned, quarantined = split_and_save(df, paths)

    # Step 6: Generate report
    report = generate_report(
        raw_count, cleaned, quarantined,
        issues_found, dupe_count, paths, start_time
    )

    # Final summary to console
    logger.info("=" * 60)
    logger.info("CLEANING COMPLETE — SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Raw rows:         {raw_count:>8,}")
    logger.info(f"  Cleaned rows:     {len(cleaned):>8,}")
    logger.info(f"  Quarantined rows: {len(quarantined):>8,}")
    logger.info(f"  Retention rate:   {len(cleaned)/raw_count*100:>7.2f}%")
    logger.info(f"  Duration:         {(datetime.now()-start_time).total_seconds():.2f}s")
    logger.info("=" * 60)
    logger.info("Next step: Run 02_score_difficulty.py")
    logger.info("=" * 60)

    return report

# ENTRY POINT
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Step 1: Clean raw JEE/NEET CSV dataset"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/raw/Jee_Neet_subjectsquestions.csv",
        help="Path to raw CSV file (relative to project root or absolute)"
    )
    args = parser.parse_args()

    report = run_cleaning_pipeline(args.input)

    # Print key numbers for quick verification
    print("\n" + "=" * 60)
    print("QUICK VERIFICATION NUMBERS")
    print("=" * 60)
    print(f"Retention rate: {report['data_summary']['retention_rate_pct']}%")
    print(f"Subject distribution: {report['cleaned_dataset_stats']['subject_distribution']}")
    print(f"LaTeX rows: {report['cleaned_dataset_stats']['rows_with_latex']:,} "
          f"({report['cleaned_dataset_stats']['latex_pct']}%)")
    print(f"MCQ option rows: {report['cleaned_dataset_stats']['rows_with_mcq_options']:,} "
          f"({report['cleaned_dataset_stats']['mcq_pct']}%)")