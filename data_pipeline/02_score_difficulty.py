"""
PURPOSE:
    Assign three parameterized fields to every question in cleaned.csv:
        1. difficulty_score    — continuous 0.0–1.0 composite signal
        2. difficulty_level    — 'Beginner' | 'Intermediate' | 'Advanced'
        3. estimated_time      — seconds (integer), predicted time-on-task
INPUTS:
    data/processed/cleaned.csv          (from 01_clean.py)
OUTPUTS:
    data/processed/difficulty_scored.csv     — full dataset with new columns
    data/reports/difficulty_thresholds.json  — per-subject p33/p67 cutoffs
    data/reports/difficulty_report.json      — full audit report
"""

import os
import re
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

# Scoring weights — must sum to 1.0 
SCORING_WEIGHTS = {
    "length":        0.25,   # Longer questions require more reading + more complex setup
    "formula":       0.25,   # Formula density is strongest single difficulty signal
    "symbol":        0.20,   # Greek symbols and mathematical notation = conceptual depth
    "question_type": 0.20,   # Question format (Assertion-Reason etc.) adds cognitive load
    "keyword":       0.10,   # Subject-specific advanced concept keywords
}

# Validation
assert abs(sum(SCORING_WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"


# Characters at which length_score reaches 1.0.
LENGTH_NORMALIZATION_ANCHOR = 500

# A question with this many LaTeX formula commands gets formula_score = 1.0
FORMULA_COUNT_ANCHOR = 5

# Symbol density normalization 
SYMBOL_COUNT_ANCHOR = 3

# Keyword count for full keyword_score
KEYWORD_COUNT_ANCHOR = 3

# Estimated time base values (seconds) per subject
BASE_TIME_SECONDS = {
    "Physics":   90,
    "Chemistry": 75,
    "Maths":     120,
    "Biology":   60,
}
TIME_MIN_SECONDS = 30
TIME_MAX_SECONDS = 300

# Subject-specific advanced concept keyword lists
ADVANCED_KEYWORDS = {
    "Physics": [
        "kirchhoff", "capacitance", "impedance", "torque", "angular momentum",
        "photoelectric effect", "lorentz force", "entropy", "carnot",
        "doppler", "interference", "diffraction", "quantum", "uncertainty",
        "heisenberg", "wave function", "de broglie", "radioactive", "nuclear fission",
        "nuclear fusion", "binding energy", "compton", "biot-savart",
        "faraday's law", "lenz's law", "resonance", "damping", "viscosity",
        "bernoulli", "moment of inertia", "centripetal", "gravitational potential",
    ],
    "Chemistry": [
        "hybridization", "electronegativity", "oxidation state", "huckel",
        "chirality", "enantiomer", "nucleophile", "electrophile", "gibbs",
        "equilibrium constant", "le chatelier", "faraday", "electrolysis",
        "coordination compound", "ligand", "crystal field", "entropy",
        "enthalpy", "activation energy", "rate constant", "arrhenius",
        "conjugate acid", "buffer solution", "solubility product",
        "van der waals", "hydrogen bonding", "dipole moment",
    ],
    "Maths": [
        "differential equation", "integration by parts", "complex number",
        "de moivre", "argand plane", "taylor series", "maclaurin series",
        "convergence", "divergence", "determinant", "eigenvalue", "eigenvector",
        "bayes theorem", "binomial theorem", "rolle's theorem", "lagrange",
        "mean value theorem", "epsilon delta", "continuity", "differentiability",
        "vector space", "linear transformation", "characteristic equation",
    ],
    "Biology": [
        "meiosis", "mitosis", "prophase", "chromosomal crossover",
        "transcription", "translation", "operon", "allele", "genotype",
        "phenotype", "hardy-weinberg", "atp synthase", "photophosphorylation",
        "calvin cycle", "krebs cycle", "chemiosmosis", "transgenic",
        "restriction enzyme", "recombinant dna", "polymerase chain reaction",
        "lymphocyte", "antibody", "antigen", "immunoglobulin",
    ],
}

# Question type patterns 
QUESTION_TYPE_PATTERNS = [
    # (pattern, is_regex, time_bonus_seconds, type_score_bonus, label)
    (r"Assertion.*Reason|Reason.*Assertion",   True,  15, 0.30, "assertion_reason"),
    (r"Match.*Column|Match.*List|List.*I.*II", True,  25, 0.50, "match_column"),
    (r"\(i\).*\(ii\)",                         True,  20, 0.30, "multi_part"),
    ("calculate",                              False, 20, 0.20, "numerical_calculate"),
    ("find the value",                         False, 15, 0.20, "numerical_find"),
    ("determine",                              False, 12, 0.15, "numerical_determine"),
    ("prove that",                             False, 25, 0.35, "proof"),
    ("derive",                                 False, 20, 0.30, "derivation"),
    ("arrange in",                             False, 10, 0.15, "arrangement"),
    (r"EXCEPT|INCORRECT|NOT correct|false",    True,   5, 0.10, "negative_assertion"),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# SIGNAL EXTRACTORS (reused 121k times)
_RE_FORMULA = re.compile(
    r"\\frac|\\sqrt|\\int(?:egral)?|\\lim|\\sum|\\prod|\\oint|\\partial|\\nabla"
    r"|\\cdot|\\times|\\pm|\\mp|\\infty|\\log|\\ln|\\exp"
)

# Symbol patterns — Greek letters and mathematical symbols
_RE_SYMBOL = re.compile(
    r"\\(?:alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda"
    r"|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega"
    r"|Alpha|Beta|Gamma|Delta|Epsilon|Theta|Lambda|Mu|Pi|Sigma|Phi|Omega"
    r"|vec|hat|bar|dot|ddot|tilde|overline|underline)"
)

# LaTeX block detection (marks a row as having structured math)
_RE_LATEX_BLOCK = re.compile(r"\\\(|\\\[|\\begin\{")


def extract_length_score(text: str) -> float:
    return min(len(text) / LENGTH_NORMALIZATION_ANCHOR, 1.0)


def extract_formula_score(text: str) -> float:
    count = len(_RE_FORMULA.findall(text))
    return min(count / FORMULA_COUNT_ANCHOR, 1.0)


def extract_symbol_score(text: str) -> float:
    count = len(_RE_SYMBOL.findall(text))
    return min(count / SYMBOL_COUNT_ANCHOR, 1.0)


def extract_question_type_score(text: str) -> tuple[float, str, int]:
    text_lower = text.lower()
    total_score_bonus = 0.0
    total_time_bonus = 0
    detected_types = []

    for pattern, is_regex, time_bonus, score_bonus, label in QUESTION_TYPE_PATTERNS:
        if is_regex:
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            except re.error:
                match = None
        else:
            match = pattern in text_lower

        if match:
            detected_types.append(label)
            total_score_bonus += score_bonus
            total_time_bonus += time_bonus

    detected_type_str = "|".join(detected_types) if detected_types else "standard_mcq"
    return min(total_score_bonus, 1.0), detected_type_str, total_time_bonus


def extract_keyword_score(text: str, subject: str) -> float:
    text_lower = text.lower()
    keywords = ADVANCED_KEYWORDS.get(subject, [])
    hit_count = sum(1 for kw in keywords if kw in text_lower)
    return min(hit_count / KEYWORD_COUNT_ANCHOR, 1.0)

# COMPOSITE SCORER
def compute_difficulty_score(text: str, subject: str) -> dict:
    s_length  = extract_length_score(text)
    s_formula = extract_formula_score(text)
    s_symbol  = extract_symbol_score(text)
    s_type, q_type, time_bonus = extract_question_type_score(text)
    s_keyword = extract_keyword_score(text, subject)

    composite = (
        SCORING_WEIGHTS["length"]        * s_length  +
        SCORING_WEIGHTS["formula"]       * s_formula +
        SCORING_WEIGHTS["symbol"]        * s_symbol  +
        SCORING_WEIGHTS["question_type"] * s_type    +
        SCORING_WEIGHTS["keyword"]       * s_keyword
    )

    return {
        "difficulty_score":   round(float(composite), 6),
        "score_length":       round(float(s_length), 4),
        "score_formula":      round(float(s_formula), 4),
        "score_symbol":       round(float(s_symbol), 4),
        "score_type":         round(float(s_type), 4),
        "score_keyword":      round(float(s_keyword), 4),
        "question_type":      q_type,
        "raw_formula_count":  len(_RE_FORMULA.findall(text)),
        "raw_symbol_count":   len(_RE_SYMBOL.findall(text)),
        "has_latex":          bool(_RE_LATEX_BLOCK.search(text)),
        "time_bonus_seconds": time_bonus,
    }
# ESTIMATED TIME MODEL
def compute_estimated_time(text: str, subject: str, time_bonus: int) -> int:
    base = BASE_TIME_SECONDS.get(subject, 90)

    # Length bonus (above 150 char baseline)
    length_bonus = max(0, (len(text) - 150) * 0.15)

    # Formula complexity bonus
    formula_count = len(_RE_FORMULA.findall(text))
    formula_bonus = min(formula_count * 8, 40)

    raw_time = base + length_bonus + formula_bonus + time_bonus
    clamped = int(max(TIME_MIN_SECONDS, min(TIME_MAX_SECONDS, raw_time)))

    return clamped

# BATCH PROCESSING
def score_all_questions(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Scoring {len(df):,} questions. This will take ~30–60 seconds...")

    results = []
    total = len(df)
    log_every = 10_000

    for i, row in enumerate(df.itertuples(index=False)):
        if i % log_every == 0 and i > 0:
            pct = i / total * 100
            logger.info(f"  Progress: {i:>7,} / {total:,}  ({pct:.1f}%)")

        score_dict = compute_difficulty_score(row.eng, row.Subject)
        est_time = compute_estimated_time(
            row.eng, row.Subject, score_dict["time_bonus_seconds"]
        )
        score_dict["estimated_time"] = est_time
        results.append(score_dict)

    logger.info(f"  Progress: {total:,} / {total:,}  (100.0%) — Scoring complete")

    scores_df = pd.DataFrame(results)
    df = df.reset_index(drop=True)
    df = pd.concat([df, scores_df], axis=1)

    return df


# PER-SUBJECT PERCENTILE TERTILE BINNING
def apply_tertile_binning(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    logger.info("Applying per-subject percentile tertile binning...")

    df["difficulty_level"] = ""
    thresholds = {}

    for subject in df["Subject"].unique():
        mask = df["Subject"] == subject
        subdf = df.loc[mask, "difficulty_score"]

        p33 = float(subdf.quantile(0.3333))
        p67 = float(subdf.quantile(0.6667))

        # Handle edge case: if p33 == p67 (very flat distribution),
        # nudge thresholds apart to avoid all-Intermediate
        if p33 >= p67:
            p33 = float(subdf.quantile(0.30))
            p67 = float(subdf.quantile(0.70))
            logger.warning(
                f"{subject}: degenerate tertile distribution detected. "
                f"Adjusted to p30={p33:.4f}, p70={p67:.4f}"
            )

        conditions = [
            subdf <= p33,
            (subdf > p33) & (subdf <= p67),
            subdf > p67,
        ]
        labels = ["Beginner", "Intermediate", "Advanced"]

        for cond, label in zip(conditions, labels):
            df.loc[mask & cond, "difficulty_level"] = label

        thresholds[subject] = {
            "p33": round(p33, 6),
            "p67": round(p67, 6),
            "count": int(mask.sum()),
        }

        dist = df.loc[mask, "difficulty_level"].value_counts()
        logger.info(
            f"  {subject:<12}: p33={p33:.4f}, p67={p67:.4f} | "
            f"Beginner={dist.get('Beginner',0):>5,}  "
            f"Intermediate={dist.get('Intermediate',0):>5,}  "
            f"Advanced={dist.get('Advanced',0):>5,}"
        )

    logger.info("Tertile binning complete.")
    return df, thresholds

# PATH RESOLUTION
def resolve_paths(input_csv: str) -> dict:
    script_dir = Path(__file__).parent
    paths = {
        "input":      Path(input_csv) if os.path.isabs(input_csv)
                      else script_dir / input_csv,
        "output":     script_dir / "data" / "processed" / "difficulty_scored.csv",
        "thresholds": script_dir / "data" / "reports" / "difficulty_thresholds.json",
        "report":     script_dir / "data" / "reports" / "difficulty_report.json",
    }
    paths["output"].parent.mkdir(parents=True, exist_ok=True)
    paths["thresholds"].parent.mkdir(parents=True, exist_ok=True)
    return paths

# REPORT GENERATION
def generate_report(
    df: pd.DataFrame,
    thresholds: dict,
    paths: dict,
    weights: dict,
    start_time: datetime,
) -> dict:
    """Generate full audit report."""
    duration = (datetime.now() - start_time).total_seconds()

    # Global difficulty distribution
    global_dist = df["difficulty_level"].value_counts().to_dict()

    # Per-subject distribution
    per_subject = {}
    for subject in df["Subject"].unique():
        subdf = df[df["Subject"] == subject]
        dist = subdf["difficulty_level"].value_counts().to_dict()
        score_stats = subdf["difficulty_score"].describe()
        time_stats = subdf["estimated_time"].describe()
        per_subject[subject] = {
            "difficulty_distribution": {k: int(v) for k, v in dist.items()},
            "score_stats": {
                k: round(float(v), 4) for k, v in score_stats.items()
                if k in ["mean", "std", "min", "50%", "max"]
            },
            "time_stats": {
                k: round(float(v), 1) for k, v in time_stats.items()
                if k in ["mean", "std", "min", "50%", "max"]
            },
        }

    # Question type distribution
    type_dist = df["question_type"].value_counts().head(15).to_dict()

    # Score signal statistics
    signal_stats = {}
    for col in ["score_length","score_formula","score_symbol","score_type","score_keyword"]:
        signal_stats[col] = {
            "mean": round(float(df[col].mean()), 4),
            "std":  round(float(df[col].std()), 4),
            "max":  round(float(df[col].max()), 4),
        }

    report = {
        "pipeline_step": "02_score_difficulty.py",
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": round(duration, 2),
        "configuration": {
            "scoring_weights": weights,
            "binning_strategy": "per_subject_percentile_tertile",
            "length_anchor": LENGTH_NORMALIZATION_ANCHOR,
            "formula_anchor": FORMULA_COUNT_ANCHOR,
            "time_min_s": TIME_MIN_SECONDS,
            "time_max_s": TIME_MAX_SECONDS,
        },
        "global_difficulty_distribution": {k: int(v) for k, v in global_dist.items()},
        "per_subject_analysis": per_subject,
        "question_type_distribution": {k: int(v) for k, v in type_dist.items()},
        "signal_statistics": signal_stats,
        "thresholds_applied": thresholds,
        "output_path": str(paths["output"]),
    }

    with open(paths["report"], "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=lambda x: int(x) if isinstance(x, np.integer) else float(x))

    # Save thresholds separately (used by FastAPI adaptive engine)
    with open(paths["thresholds"], "w", encoding="utf-8") as f:
        json.dump(thresholds, f, indent=2)

    logger.info(f"Audit report saved: {paths['report']}")
    logger.info(f"Thresholds saved:   {paths['thresholds']}")
    return report

# PIPELINE ORCHESTRATOR
def run_difficulty_pipeline(
    input_csv: str,
    weights: Optional[list] = None,
) -> dict:

    start_time = datetime.now()
    logger.info("=" * 65)
    logger.info("02_score_difficulty.py — Starting Difficulty Scoring Pipeline")
    logger.info("=" * 65)

    # Apply custom weights if provided via CLI
    if weights:
        keys = ["length", "formula", "symbol", "question_type", "keyword"]
        for k, v in zip(keys, weights):
            SCORING_WEIGHTS[k] = v
        total = sum(SCORING_WEIGHTS.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Custom weights must sum to 1.0. Got {total:.4f}. "
                f"Values: {SCORING_WEIGHTS}"
            )
        logger.info(f"Using custom weights: {SCORING_WEIGHTS}")
    else:
        logger.info(f"Using default weights: {SCORING_WEIGHTS}")

    # Resolve paths
    paths = resolve_paths(input_csv)

    # Load cleaned data
    logger.info(f"Loading cleaned dataset: {paths['input']}")
    df = pd.read_csv(paths["input"], dtype={"row_id": int})
    logger.info(f"Loaded {len(df):,} rows")

    # Validate required columns
    required = {"row_id", "eng", "Subject"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Score all questions
    df = score_all_questions(df)

    # Apply tertile binning
    df, thresholds = apply_tertile_binning(df)

    # Select and order output columns
    output_columns = [
        "row_id",
        "eng",
        "Subject",
        "difficulty_level",
        "difficulty_score",
        "estimated_time",
        "question_type",
        "has_latex",
        "raw_formula_count",
        "raw_symbol_count",
        # Individual signal scores (useful for model auditing)
        "score_length",
        "score_formula",
        "score_symbol",
        "score_type",
        "score_keyword",
    ]

    df_output = df[output_columns]

    # Save output
    df_output.to_csv(paths["output"], index=False, encoding="utf-8")
    logger.info(f"Scored dataset saved: {len(df_output):,} rows → {paths['output']}")

    # Generate report
    report = generate_report(df_output, thresholds, paths, SCORING_WEIGHTS, start_time)

    # Final summary
    duration = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 65)
    logger.info("DIFFICULTY SCORING COMPLETE — SUMMARY")
    logger.info("=" * 65)
    logger.info(f"  Total rows scored:  {len(df_output):,}")
    logger.info(f"  Duration:           {duration:.1f}s")
    logger.info("")
    logger.info("  GLOBAL DISTRIBUTION:")
    for level in ["Beginner", "Intermediate", "Advanced"]:
        count = (df_output["difficulty_level"] == level).sum()
        pct = count / len(df_output) * 100
        logger.info(f"    {level:<14}: {count:>7,}  ({pct:.1f}%)")
    logger.info("")
    logger.info("  ESTIMATED TIME (seconds):")
    logger.info(f"    Mean:   {df_output['estimated_time'].mean():.1f}s")
    logger.info(f"    Median: {df_output['estimated_time'].median():.1f}s")
    logger.info(f"    Min:    {df_output['estimated_time'].min()}s")
    logger.info(f"    Max:    {df_output['estimated_time'].max()}s")
    logger.info("=" * 65)
    logger.info("Next step: Run 03_extract_topics.py")
    logger.info("=" * 65)

    return report

# ENTRY POINT
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Step 2: Score difficulty and estimate time for all questions"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/processed/cleaned.csv",
        help="Path to cleaned.csv (relative to data_pipeline/ or absolute)"
    )
    parser.add_argument(
        "--weights",
        type=float,
        nargs=5,
        metavar=("W_LENGTH", "W_FORMULA", "W_SYMBOL", "W_TYPE", "W_KEYWORD"),
        help=(
            "Custom scoring weights (5 floats, must sum to 1.0). "
            "Example: --weights 0.30 0.30 0.15 0.15 0.10"
        ),
        default=None,
    )
    args = parser.parse_args()

    report = run_difficulty_pipeline(
        input_csv=args.input,
        weights=args.weights,
    )

    # Quick verification printout
    print("\n" + "=" * 65)
    print("QUICK VERIFICATION — GLOBAL DIFFICULTY DISTRIBUTION")
    print("=" * 65)
    dist = report["global_difficulty_distribution"]
    total = sum(dist.values())
    for level in ["Beginner", "Intermediate", "Advanced"]:
        count = dist.get(level, 0)
        pct = count / total * 100
        print(f"  {level:<14}: {count:>7,}  ({pct:.1f}%)")

    print("\nPER-SUBJECT DIFFICULTY DISTRIBUTION:")
    for subject, data in report["per_subject_analysis"].items():
        d = data["difficulty_distribution"]
        print(f"  {subject}:")
        for level in ["Beginner", "Intermediate", "Advanced"]:
            print(f"    {level:<14}: {d.get(level, 0):>6,}")

    print("\nESTIMATED TIME PER SUBJECT (mean seconds):")
    for subject, data in report["per_subject_analysis"].items():
        print(f"  {subject:<12}: {data['time_stats']['mean']:.1f}s")