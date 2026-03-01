"""
PURPOSE:
    Generate 384-dimensional dense vector embeddings for all 121,557
    question texts using BAAI/bge-small-en-v1.5, and save them in a
    binary format optimized for Supabase pgvector ingestion.
INPUTS:
    data/processed/topics_extracted.csv    (from 03_extract_topics.py)

OUTPUTS:
    data/processed/embeddings_matrix.npy  — float32 matrix (178MB)
    data/processed/embeddings_metadata.csv — metadata per row
    data/processed/checkpoint.json  — resume state (deleted on success)
    data/reports/embeddings_report.json — full audit report
"""
import os
import json
import math
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd

MODEL_NAME          = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM       = 384
EMBEDDING_DTYPE     = np.float32
BATCH_SIZE_BY_DEVICE: dict = {
    "cpu":  128,
    "mps":  64,    #safe for long sequences up to 512 tokens
    "cuda": 256,   
}
DEFAULT_CHECKPOINT_EVERY = 30
NORM_TOLERANCE_LOW  = 0.98
NORM_TOLERANCE_HIGH = 1.02

# No. sample norms to log in the report
NORM_SAMPLE_SIZE    = 1000

# Progress log interval (rows)
LOG_EVERY_ROWS      = 5_000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)



# PATH RESOLUTION
def resolve_paths(input_csv: str) -> dict:
    script_dir = Path(__file__).parent
    paths = {
        "input":      Path(input_csv) if os.path.isabs(input_csv)
                      else script_dir / input_csv,
        "matrix":     script_dir / "data" / "processed" / "embeddings_matrix.npy",
        "metadata":   script_dir / "data" / "processed" / "embeddings_metadata.csv",
        "checkpoint": script_dir / "data" / "processed" / "checkpoint.json",
        "report":     script_dir / "data" / "reports"   / "embeddings_report.json",
    }
    paths["matrix"].parent.mkdir(parents=True, exist_ok=True)
    paths["report"].parent.mkdir(parents=True, exist_ok=True)
    return paths



# CHECKPOINT MANAGEMENT
def load_checkpoint(checkpoint_path: Path) -> Optional[dict]:
    if not checkpoint_path.exists():
        return None
    try:
        with open(checkpoint_path, "r") as f:
            ckpt = json.load(f)
        required = {"last_completed_batch", "total_batches", "rows_completed",
                    "total_rows", "batch_size", "model_name"}
        if not required.issubset(ckpt.keys()):
            logger.warning("Checkpoint file exists but is malformed. Ignoring.")
            return None
        logger.info(f"Checkpoint found: {ckpt['rows_completed']:,} / "
                    f"{ckpt['total_rows']:,} rows completed "
                    f"(batch {ckpt['last_completed_batch']+1} / {ckpt['total_batches']})")
        return ckpt
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Checkpoint file unreadable: {e}. Starting fresh.")
        return None

def save_checkpoint(
    checkpoint_path: Path,
    last_batch: int,
    total_batches: int,
    rows_completed: int,
    total_rows: int,
    batch_size: int,
    started_at: str,
) -> None:
    """Write checkpoint state to disk atomically."""
    ckpt = {
        "last_completed_batch": last_batch,
        "total_batches":        total_batches,
        "rows_completed":       rows_completed,
        "total_rows":           total_rows,
        "model_name":           MODEL_NAME,
        "batch_size":           batch_size,
        "started_at":           started_at,
        "last_updated":         datetime.now().isoformat(),
    }
    # Write to tmp first then rename for atomicity
    tmp_path = checkpoint_path.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(ckpt, f, indent=2)
    tmp_path.rename(checkpoint_path)


def delete_checkpoint(checkpoint_path: Path) -> None:
    """Remove checkpoint after successful completion."""
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        logger.info("Checkpoint deleted (pipeline completed successfully).")

# DEVICE DETECTION
def detect_device() -> str:
    try:
        import torch
        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def get_device_description(device: str) -> str:
    """Return a human-readable description of the detected device."""
    try:
        import torch
        if device == "mps":
            # Apple Silicon: chip info available via platform
            import platform
            chip = platform.processor() or "Apple Silicon"
            return f"Apple Silicon GPU via MPS ({chip})"
        if device == "cuda":
            name = torch.cuda.get_device_name(0)
            mem  = torch.cuda.get_device_properties(0).total_memory / 1024**3
            return f"NVIDIA GPU: {name} ({mem:.1f} GB VRAM)"
    except Exception:
        pass
    return "CPU (no GPU acceleration)"

# MODEL LOADING
def load_model(device: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers is not installed.\n"
            "Install it with: pip install sentence-transformers\n"
            "This should already be present from your Phase 1 setup."
        )

    logger.info(f"Loading model: {MODEL_NAME}")
    logger.info(f"  Target device:     {device.upper()}  ({get_device_description(device)})")
    logger.info(f"  First run:         downloads ~130MB to ~/.cache/huggingface/")
    logger.info(f"  Subsequent runs:   loads from local cache (~3s)")

    t0 = time.perf_counter()
    model = SentenceTransformer(MODEL_NAME, device=device)
    elapsed = time.perf_counter() - t0

    logger.info(f"Model loaded in {elapsed:.1f}s")
    logger.info(f"  Max sequence length: {model.max_seq_length}")
    logger.info(f"  Output dimension:    {EMBEDDING_DIM}")
    logger.info(f"  Active device:       {device.upper()}")

    if device in ("mps", "cuda"):
        logger.info(f"  Warming up {device.upper()} (Metal shader compilation)...")
        warmup_texts = ["warmup sentence for Metal shader compilation"] * 8
        _ = model.encode(warmup_texts, batch_size=8,
                         normalize_embeddings=True, show_progress_bar=False)
        logger.info(f"  Warmup complete.")
    actual_batch = BATCH_SIZE_BY_DEVICE.get(device, 64)
    benchmark_texts = (
        # Mix of short, medium, and long texts — reflects real dataset
        ["What is the photoelectric effect?"] * (actual_batch // 4) +
        ["A particle of mass m moves with uniform speed v along the perimeter "
         "of a regular hexagon inscribed in a circle of radius R. "
         "Calculate the magnitude of impulse at each corner of the hexagon."] * (actual_batch // 4) +
        ["Given: \\( \\frac{d^2y}{dx^2} + 3\\frac{dy}{dx} + 2y = e^x \\). "
         "Find the particular solution satisfying y(0)=0, y'(0)=1. "
         "A. \\( e^{-x} - e^{-2x} + \\frac{e^x}{6} \\) "
         "B. \\( e^{-x} + e^{-2x} \\) "
         "C. \\( \\frac{e^x}{6} - e^{-x} \\) "
         "D. \\( 2e^{-x} - e^{-2x} \\)"] * (actual_batch // 2)
    )[:actual_batch]

    t_bench = time.perf_counter()
    _ = model.encode(benchmark_texts, batch_size=actual_batch,
                     normalize_embeddings=True, show_progress_bar=False)
    bench_elapsed = time.perf_counter() - t_bench
    bench_throughput = actual_batch / bench_elapsed

    logger.info(f"  Benchmark ({actual_batch} samples, realistic lengths): "
                f"{bench_elapsed*1000:.0f}ms → {bench_throughput:.0f} rows/sec")

    if device == "mps":
        eta_min = 121_557 / bench_throughput / 60
        logger.info(f"  Estimated full run: ~{eta_min:.1f} min at current throughput")
        if bench_throughput < 150:
            logger.warning(
                f"  MPS throughput ({bench_throughput:.0f} rows/sec) is very low. "
                f"If this is slower than CPU, run: python 04_generate_embeddings.py --device cpu"
            )

    return model, device

# TEXT PREPROCESSING FOR EMBEDDING
def prepare_text_for_embedding(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.strip()
    # Collapse multiple newlines to single space
    # This keeps MCQ options as a continuous sequence
    import re
    text = re.sub(r'\n+', ' ', text)
    # Collapse multiple spaces to single
    text = re.sub(r' {2,}', ' ', text)
    return text

# BATCH EMBEDDING ENGINE
def generate_embeddings(
    texts: list[str],
    model,
    batch_size: int,
    matrix: np.ndarray,
    start_batch: int,
    total_batches: int,
    checkpoint_path: Path,
    checkpoint_every: int,
    started_at: str,
    total_rows: int,
) -> tuple[np.ndarray, dict]:
    timing_stats = {
        "batch_times_ms": [],
        "rows_processed": 0,
        "batches_processed": 0,
    }

    last_log_row = start_batch * batch_size

    for batch_idx in range(start_batch, total_batches):
        batch_start = batch_idx * batch_size
        batch_end   = min(batch_start + batch_size, total_rows)
        batch_texts = texts[batch_start:batch_end]
        current_batch_size = len(batch_texts)

        # ── Encode this batch ──────────────────────────────────────────
        t_batch_start = time.perf_counter()

        batch_embeddings = model.encode(
            batch_texts,
            batch_size=current_batch_size,   # encode full batch in one call
            normalize_embeddings=True,        # unit vectors for cosine similarity
            show_progress_bar=False,          # we have our own logging
            convert_to_numpy=True,            # return np.ndarray directly
        )

        t_batch_elapsed_ms = (time.perf_counter() - t_batch_start) * 1000

        # Write to pre-allocated matrix 
        matrix[batch_start:batch_end] = batch_embeddings.astype(EMBEDDING_DTYPE)

        timing_stats["batch_times_ms"].append(t_batch_elapsed_ms)
        timing_stats["rows_processed"]  += current_batch_size
        timing_stats["batches_processed"] += 1

        rows_done = batch_end

        # Progress logging 
        if rows_done - last_log_row >= LOG_EVERY_ROWS or batch_idx == total_batches - 1:
            pct = rows_done / total_rows * 100
            ms_per_row = t_batch_elapsed_ms / current_batch_size
            throughput = 1000 / ms_per_row if ms_per_row > 0 else 0
            eta_rows = total_rows - rows_done
            eta_sec = eta_rows / throughput if throughput > 0 else 0
            logger.info(
                f"  [{rows_done:>7,} / {total_rows:,}]  {pct:>5.1f}%  "
                f"| batch {batch_idx+1:>4}/{total_batches}  "
                f"| {throughput:>5.0f} rows/s  "
                f"| ETA: {eta_sec:.0f}s"
            )
            last_log_row = rows_done

        # Checkpoint flush 
        if (batch_idx + 1) % checkpoint_every == 0 or batch_idx == total_batches - 1:
            np.save(checkpoint_path.parent / "embeddings_matrix.npy", matrix)
            save_checkpoint(
                checkpoint_path   = checkpoint_path,
                last_batch        = batch_idx,
                total_batches     = total_batches,
                rows_completed    = rows_done,
                total_rows        = total_rows,
                batch_size        = batch_size,
                started_at        = started_at,
            )

    return matrix, timing_stats

# VALIDATION
def validate_embeddings(matrix: np.ndarray, total_rows: int) -> dict:
    logger.info("Running post-generation validation...")
    result = {"all_passed": True, "checks": {}}

    def check(name: str, passed: bool, detail: str):
        result["checks"][name] = {"passed": passed, "detail": detail}
        if not passed:
            result["all_passed"] = False
            logger.error(f"  FAIL — {name}: {detail}")
        else:
            logger.info(f"  PASS — {name}: {detail}")

    # 1. Shape
    expected_shape = (total_rows, EMBEDDING_DIM)
    check("shape",
          matrix.shape == expected_shape,
          f"got {matrix.shape}, expected {expected_shape}")

    # 2. dtype
    check("dtype",
          matrix.dtype == EMBEDDING_DTYPE,
          f"got {matrix.dtype}, expected {EMBEDDING_DTYPE}")

    # 3. NaN check (sample 10k rows for speed)
    sample_idx = np.random.choice(total_rows, min(10_000, total_rows), replace=False)
    has_nan = np.isnan(matrix[sample_idx]).any()
    check("no_nan_values",
          not has_nan,
          "no NaN found in sample" if not has_nan else "NaN detected!")

    # 4. Zero-row check
    row_norms_full = np.linalg.norm(matrix[sample_idx], axis=1)
    zero_rows = (row_norms_full < 1e-6).sum()
    check("no_zero_rows",
          zero_rows == 0,
          f"no zero-norm rows found" if zero_rows == 0 else f"{zero_rows} zero-norm rows!")

    # 5. Norm validation (all rows should be ~1.0 since normalize=True)
    norm_sample_idx = np.random.choice(total_rows, min(NORM_SAMPLE_SIZE, total_rows), replace=False)
    norms = np.linalg.norm(matrix[norm_sample_idx], axis=1)
    norm_min = float(norms.min())
    norm_max = float(norms.max())
    norm_mean = float(norms.mean())
    norms_ok = (norm_min >= NORM_TOLERANCE_LOW) and (norm_max <= NORM_TOLERANCE_HIGH)

    check("embedding_norms",
          norms_ok,
          f"mean={norm_mean:.6f}, min={norm_min:.6f}, max={norm_max:.6f} "
          f"(tolerance [{NORM_TOLERANCE_LOW}, {NORM_TOLERANCE_HIGH}])")

    result["norm_stats"] = {
        "mean": round(norm_mean, 8),
        "min":  round(norm_min, 8),
        "max":  round(norm_max, 8),
        "std":  round(float(norms.std()), 8),
        "sample_size": len(norm_sample_idx),
    }

    if result["all_passed"]:
        logger.info("All validation checks passed.")
    else:
        logger.error("One or more validation checks FAILED. Review before uploading.")

    return result

# METADATA CSV GENERATION
def save_metadata_csv(df: pd.DataFrame, path: Path) -> None:
    metadata_cols = [
        "row_id", "Subject", "difficulty_level", "difficulty_score",
        "estimated_time", "question_type", "has_latex",
        "raw_formula_count", "raw_symbol_count",
        "score_length", "score_formula", "score_symbol",
        "score_type", "score_keyword", "topic", "subtopic",
    ]
    # Keep only columns that exist in df (graceful handling)
    available = [c for c in metadata_cols if c in df.columns]
    df[available].to_csv(path, index=False, encoding="utf-8")
    logger.info(f"Metadata CSV saved: {len(df):,} rows → {path}")

# REPORT GENERATION
def generate_report(
    df: pd.DataFrame,
    matrix: np.ndarray,
    validation: dict,
    timing_stats: dict,
    paths: dict,
    batch_size: int,
    device: str,
    start_time: datetime,
    resumed_from_batch: Optional[int],
) -> dict:
    """Generate full audit report for research documentation."""
    duration = (datetime.now() - start_time).total_seconds()

    batch_times = timing_stats.get("batch_times_ms", [])
    rows_processed = timing_stats.get("rows_processed", 0)

    throughput = rows_processed / duration if duration > 0 else 0

    # Compute mean embedding norm (full matrix — fast with numpy)
    full_norms = np.linalg.norm(matrix, axis=1)

    report = {
        "pipeline_step": "04_generate_embeddings.py",
        "timestamp":     datetime.now().isoformat(),
        "duration_seconds": round(duration, 2),
        "model": {
            "name":               MODEL_NAME,
            "embedding_dim":      EMBEDDING_DIM,
            "dtype":              str(EMBEDDING_DTYPE),
            "normalize":          True,
            "instruction_prefix": None,
            "device":             device,
            "device_description": get_device_description(device),
        },
        "processing": {
            "total_rows":          len(df),
            "rows_processed":      rows_processed,
            "batch_size":          batch_size,
            "total_batches":       math.ceil(len(df) / batch_size),
            "throughput_rows_sec": round(throughput, 1),
            "resumed_from_batch":  resumed_from_batch,
            "avg_batch_ms":        round(float(np.mean(batch_times)), 1) if batch_times else 0,
            "p95_batch_ms":        round(float(np.percentile(batch_times, 95)), 1) if len(batch_times) > 5 else 0,
        },
        "output_files": {
            "matrix_npy":     str(paths["matrix"]),
            "matrix_shape":   list(matrix.shape),
            "matrix_size_mb": round(matrix.nbytes / 1024 / 1024, 1),
            "metadata_csv":   str(paths["metadata"]),
        },
        "embedding_statistics": {
            "norm_mean": round(float(full_norms.mean()), 8),
            "norm_std":  round(float(full_norms.std()),  8),
            "norm_min":  round(float(full_norms.min()),  8),
            "norm_max":  round(float(full_norms.max()),  8),
        },
        "validation": validation,
        "dataset_breakdown": {
            "by_subject":     df["Subject"].value_counts().to_dict(),
            "by_difficulty":  df["difficulty_level"].value_counts().to_dict(),
            "by_topic_top10": df["topic"].value_counts().head(10).to_dict(),
        },
        "pgvector_compatibility": {
            "vector_dimension": EMBEDDING_DIM,
            "supabase_type":    f"VECTOR({EMBEDDING_DIM})",
            "index_type":       "HNSW (vector_cosine_ops)",
            "upload_format":    "'[v1,v2,...,v384]'",
            "ready_for_upload": validation["all_passed"],
        },
    }

    with open(paths["report"], "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2,
                  default=lambda x: int(x) if isinstance(x, (np.integer,)) else float(x))

    logger.info(f"Report saved: {paths['report']}")
    return report

# PIPELINE ORCHESTRATOR
def run_embedding_pipeline(
    input_csv:        str,
    batch_size:       Optional[int] = None,   # None = auto-select from BATCH_SIZE_BY_DEVICE
    checkpoint_every: int = DEFAULT_CHECKPOINT_EVERY,
    fresh_start:      bool = False,
    device:           Optional[str] = None,   # None = auto-detect
) -> dict:
    
    start_time = datetime.now()
    started_at = start_time.isoformat()

    # Step 1: Device detection 
    if device is None:
        device = detect_device()

    # Step 2: Auto batch size 
    if batch_size is None:
        batch_size = BATCH_SIZE_BY_DEVICE.get(device, 128)
        batch_size_source = f"auto ({device.upper()} default)"
    else:
        batch_size_source = "manual override"

    logger.info("=" * 70)
    logger.info("04_generate_embeddings.py — Embedding Generation Pipeline")
    logger.info("=" * 70)
    logger.info(f"  Device:           {device.upper()}  — {get_device_description(device)}")
    logger.info(f"  Model:            {MODEL_NAME}")
    logger.info(f"  Embedding dim:    {EMBEDDING_DIM}")
    logger.info(f"  Batch size:       {batch_size}  ({batch_size_source})")
    logger.info(f"  Checkpoint every: {checkpoint_every} batches "
                f"(~{checkpoint_every * batch_size:,} rows)")
    logger.info("=" * 70)

    paths = resolve_paths(input_csv)

    # Step 3: Load dataset
    logger.info(f"Loading dataset: {paths['input']}")
    df = pd.read_csv(paths["input"], dtype={"row_id": int})
    logger.info(f"Loaded {len(df):,} rows, {len(df.columns)} columns")

    required_cols = {"row_id", "eng", "Subject", "difficulty_level", "topic", "subtopic"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns from input: {missing}")

    # CRITICAL: Sort by row_id — guarantees matrix row i aligns with row_id i
    df = df.sort_values("row_id", ascending=True).reset_index(drop=True)
    logger.info(f"Sorted by row_id: range [{df['row_id'].min()}, {df['row_id'].max()}]")

    total_rows    = len(df)
    total_batches = math.ceil(total_rows / batch_size)

    # Step 4: Checkpoint resume check
    resumed_from_batch = None
    start_batch        = 0

    if fresh_start:
        logger.info("--fresh flag set: ignoring any existing checkpoint.")
        delete_checkpoint(paths["checkpoint"])
    else:
        checkpoint = load_checkpoint(paths["checkpoint"])
        if checkpoint:
            if (checkpoint["total_rows"] != total_rows or
                checkpoint["batch_size"] != batch_size or
                checkpoint["model_name"] != MODEL_NAME):
                logger.warning(
                    "Checkpoint parameters mismatch "
                    "(different rows/batch_size/model). Starting fresh."
                )
                checkpoint = None

        if checkpoint and paths["matrix"].exists():
            start_batch        = checkpoint["last_completed_batch"] + 1
            resumed_from_batch = checkpoint["last_completed_batch"]
            logger.info(f"Resuming from batch {start_batch} "
                        f"({checkpoint['rows_completed']:,} rows already embedded)")
        elif checkpoint:
            logger.warning("Checkpoint found but matrix file missing. Starting fresh.")
            checkpoint = None

    # Step 5: Pre-allocate embedding matrix 
    matrix_size_mb = (total_rows * EMBEDDING_DIM * 4) / 1024 / 1024
    logger.info(f"Pre-allocating matrix: "
                f"({total_rows:,} × {EMBEDDING_DIM}) float32 = {matrix_size_mb:.1f} MB")

    if start_batch > 0 and paths["matrix"].exists():
        logger.info(f"Loading partial matrix from: {paths['matrix']}")
        matrix = np.load(paths["matrix"])
        assert matrix.shape == (total_rows, EMBEDDING_DIM), (
            f"Matrix shape mismatch: got {matrix.shape}, "
            f"expected ({total_rows}, {EMBEDDING_DIM})"
        )
        logger.info(f"Partial matrix loaded. Resuming from batch {start_batch}.")
    else:
        matrix = np.zeros((total_rows, EMBEDDING_DIM), dtype=EMBEDDING_DTYPE)
        logger.info("Zero matrix allocated. Starting from batch 0.")

    # Step 6 + 7: Load model, warmup, benchmark 
    model, device = load_model(device)

    # Step 8: Prepare texts
    logger.info("Preparing texts...")
    texts = [prepare_text_for_embedding(t) for t in df["eng"].tolist()]

    empty_count = sum(1 for t in texts if not t)
    if empty_count > 0:
        logger.warning(f"{empty_count} empty texts detected.")

    avg_len = sum(len(t) for t in texts) / len(texts)
    max_len = max(len(t) for t in texts)
    logger.info(f"Texts ready. Avg: {avg_len:.0f} chars, Max: {max_len} chars")

    # Step 9: Generate embeddings
    logger.info(f"Starting embedding: {total_batches} total batches, "
                f"first={start_batch}, last={total_batches-1}")
    logger.info("-" * 70)

    matrix, timing_stats = generate_embeddings(
        texts            = texts,
        model            = model,
        batch_size       = batch_size,
        matrix           = matrix,
        start_batch      = start_batch,
        total_batches    = total_batches,
        checkpoint_path  = paths["checkpoint"],
        checkpoint_every = checkpoint_every,
        started_at       = started_at,
        total_rows       = total_rows,
    )

    logger.info("-" * 70)
    logger.info("Embedding generation complete.")

    # Step 10: Save final matrix 
    logger.info(f"Saving matrix → {paths['matrix']}")
    np.save(paths["matrix"], matrix)
    logger.info(f"Saved: shape={matrix.shape}, dtype={matrix.dtype}, "
                f"size={matrix.nbytes/1024/1024:.1f} MB")

    # Step 11: Validate
    validation = validate_embeddings(matrix, total_rows)

    # Step 12: Save metadata CSV 
    save_metadata_csv(df, paths["metadata"])

    # Step 13: Generate report 
    report = generate_report(
        df                 = df,
        matrix             = matrix,
        validation         = validation,
        timing_stats       = timing_stats,
        paths              = paths,
        batch_size         = batch_size,
        device             = device,
        start_time         = start_time,
        resumed_from_batch = resumed_from_batch,
    )

    # Step 14: Delete checkpoint (success)
    delete_checkpoint(paths["checkpoint"])

    # Final summary
    duration   = (datetime.now() - start_time).total_seconds()
    throughput = total_rows / duration if duration > 0 else 0

    logger.info("=" * 70)
    logger.info("EMBEDDING PIPELINE COMPLETE")
    logger.info("=" * 70)
    logger.info(f"  Device:               {device.upper()}")
    logger.info(f"  Rows embedded:        {total_rows:,}")
    logger.info(f"  Duration:             {duration:.1f}s  ({duration/60:.1f} min)")
    logger.info(f"  Throughput:           {throughput:.0f} rows/sec")
    logger.info(f"  Matrix:               {matrix.shape}  {matrix.nbytes/1024/1024:.1f} MB")
    logger.info(f"  Mean norm:            {report['embedding_statistics']['norm_mean']:.8f}")
    logger.info(f"  Validation:           {'ALL PASSED' if validation['all_passed'] else 'FAILED — see report'}")
    logger.info("=" * 70)
    logger.info("Next step: python 05_upload_supabase.py")
    logger.info("=" * 70)

    return report

# ENTRY POINT
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Step 4: Generate BAAI/bge-small-en-v1.5 embeddings (MPS/CUDA/CPU)"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/processed/topics_extracted.csv",
        help="Path to topics_extracted.csv"
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["mps", "cuda", "cpu"],
        help=(
            "Compute device. Default: auto-detect. "
            "mps = Apple Silicon GPU (M1/M2/M3/M4), "
            "cuda = NVIDIA GPU, cpu = fallback."
        )
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=None,
        help=(
            "Rows per encode() call. Default: auto (mps=512, cuda=512, cpu=128). "
            "Override only if you hit memory issues."
        )
    )
    parser.add_argument(
        "--checkpoint_every",
        type=int,
        default=DEFAULT_CHECKPOINT_EVERY,
        help=f"Flush matrix to disk every N batches (default: {DEFAULT_CHECKPOINT_EVERY})."
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        default=False,
        help="Ignore any existing checkpoint and start from row 0."
    )
    args = parser.parse_args()

    # Validate batch_size only if explicitly provided
    if args.batch_size is not None and not (1 <= args.batch_size <= 2048):
        raise ValueError(f"--batch_size must be between 1 and 2048. Got: {args.batch_size}")
    if not 1 <= args.checkpoint_every <= 1000:
        raise ValueError(f"--checkpoint_every must be between 1 and 1000. Got: {args.checkpoint_every}")

    report = run_embedding_pipeline(
        input_csv        = args.input,
        batch_size       = args.batch_size,     # None = auto-select
        checkpoint_every = args.checkpoint_every,
        fresh_start      = args.fresh,
        device           = args.device,          # None = auto-detect
    )

    # Quick verification printout 
    print()
    print("=" * 70)
    print("QUICK VERIFICATION")
    print("=" * 70)
    proc = report["processing"]
    emb  = report["embedding_statistics"]
    val  = report["validation"]
    mod  = report["model"]

    print(f"  Device:               {mod['device'].upper()}  — {mod['device_description']}")
    print(f"  Batch size used:      {proc['batch_size']}")
    print(f"  Rows embedded:        {proc['total_rows']:,}")
    print(f"  Throughput:           {proc['throughput_rows_sec']} rows/sec")
    print(f"  Duration:             {report['duration_seconds']:.1f}s  "
          f"({report['duration_seconds']/60:.1f} min)")
    print()
    print(f"  Matrix shape:         {report['output_files']['matrix_shape']}")
    print(f"  Matrix size:          {report['output_files']['matrix_size_mb']} MB")
    print()
    print(f"  Mean norm:            {emb['norm_mean']:.8f}  (expected: ~1.0)")
    print(f"  Norm range:           [{emb['norm_min']:.6f}, {emb['norm_max']:.6f}]")
    print()
    print(f"  Validation:           {'ALL PASSED ✓' if val['all_passed'] else 'FAILED ✗ — check report'}")
    print(f"  Ready for upload:     {report['pgvector_compatibility']['ready_for_upload']}")
    print()
    print("Output files:")
    print(f"  {report['output_files']['matrix_npy']}")
    print(f"  {report['output_files']['metadata_csv']}")