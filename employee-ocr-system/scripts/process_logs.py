import gzip
import logging
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
INPUT_FILE = OUTPUTS_DIR / "logs.csv"
COMPRESSED_LOGS_FILE = OUTPUTS_DIR / "compressed_logs.csv"
GROUPED_LOGS_FILE = OUTPUTS_DIR / "grouped_logs.csv"
TIME_COMPRESSED_FILE = OUTPUTS_DIR / "time_compressed.csv"
SUMMARY_FILE = OUTPUTS_DIR / "summary.csv"
FINAL_CSV_FILE = OUTPUTS_DIR / "final_logs.csv"
FINAL_GZIP_FILE = OUTPUTS_DIR / "final_logs.csv.gz"


ACTIVITY_KEYWORDS: Dict[str, Iterable[str]] = {
    "gmail": ("gmail", "mail.google", "inbox", "compose mail", "google mail"),
    "youtube": ("youtube", "youtu.be", "watch later", "youtube studio"),
    "vscode": ("vscode", "visual studio code", "code.exe", "terminal", ".py", ".js", ".html"),
    "excel": ("excel", ".xlsx", ".xls", "spreadsheet", "worksheet", "formula bar"),
    "chrome": ("chrome", "google chrome", "new tab", "omnibox", "chrome.exe"),
    "word": ("word", "document", ".docx", ".doc", "microsoft word"),
    "powerpoint": ("powerpoint", "presentation", ".pptx", ".ppt", "slide show"),
    "teams": ("teams", "meeting", "microsoft teams", "call ended", "calendar"),
    "slack": ("slack", "workspace", "channel", "huddle"),
    "github": ("github", "pull request", "commit", "repository", "branch"),
    "file_explorer": ("downloads", "file explorer", "this pc", "desktop", "folder"),
    "security": ("firewall", "windows security", "blocked", "unauthorized", "credential", "token"),
}


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def log_step(message: str) -> None:
    logging.info(message)


def normalize_column_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def load_csv(input_path: Path) -> pd.DataFrame:
    log_step(f"Loading CSV from {input_path}")

    if not input_path.exists():
        logging.warning("Input file does not exist. Returning empty dataset.")
        return pd.DataFrame()

    try:
        frame = pd.read_csv(input_path)
    except pd.errors.EmptyDataError:
        logging.warning("Input file is empty. Returning empty dataset.")
        return pd.DataFrame()

    frame.columns = [normalize_column_name(column) for column in frame.columns]
    log_step(f"Loaded {len(frame)} rows with columns: {list(frame.columns)}")
    return frame


def find_first_existing_column(frame: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return None


def ensure_text_column(frame: pd.DataFrame) -> pd.DataFrame:
    log_step("Ensuring Text column is available")

    if frame.empty:
        frame["Text"] = pd.Series(dtype="object")
        return frame

    text_source = find_first_existing_column(frame, ["text", "ocr_text"])
    if text_source is None:
        logging.warning("No text-like column found. Creating empty Text column.")
        frame["Text"] = ""
        return frame

    frame["Text"] = frame[text_source].fillna("").astype(str).str.strip()
    return frame


def extract_employee_from_path(path_value: str) -> str:
    path_text = str(path_value or "").strip()
    if not path_text:
        return "unknown"

    normalized = path_text.replace("\\", "/").strip("/")
    parts = [part for part in normalized.split("/") if part]

    screenshot_indexes = [index for index, part in enumerate(parts) if part.lower() == "screenshots"]
    for index in reversed(screenshot_indexes):
        if index + 1 < len(parts):
            candidate = parts[index + 1]
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", candidate):
                continue
            if candidate.lower() != "media":
                return candidate

    stem = Path(path_text).stem
    match = re.match(r"rec_([a-zA-Z0-9_]+)_\d{10,}", stem)
    if match:
        return match.group(1)

    return "unknown"


def ensure_employee_column(frame: pd.DataFrame) -> pd.DataFrame:
    log_step("Ensuring Employee column is available")

    if frame.empty:
        frame["Employee"] = pd.Series(dtype="object")
        return frame

    employee_source = find_first_existing_column(frame, ["employee", "employee_name", "employee_code"])
    path_source = find_first_existing_column(frame, ["file_name", "filename", "image_path", "file"])

    if employee_source:
        employee_series = frame[employee_source].fillna("").astype(str).str.strip()
        if employee_source == "employee_code" and path_source:
            derived = frame[path_source].fillna("").map(extract_employee_from_path)
            employee_series = employee_series.where(~employee_series.str.fullmatch(r"\d{4}-\d{2}-\d{2}"), derived)
            employee_series = employee_series.where(employee_series.ne(""), derived)
        frame["Employee"] = employee_series.replace("", "unknown")
        return frame

    if path_source:
        frame["Employee"] = frame[path_source].fillna("").map(extract_employee_from_path)
        return frame

    logging.warning("Employee column could not be inferred. Using 'unknown'.")
    frame["Employee"] = "unknown"
    return frame


def extract_timestamp_from_path(path_value: str) -> pd.Timestamp:
    path_text = str(path_value or "")
    match = re.search(r"_(\d{10,})(?:_[^\\/]+)?\.[A-Za-z0-9]+$", path_text)
    if not match:
        return pd.NaT

    raw_value = match.group(1)
    try:
        return pd.to_datetime(int(raw_value), unit="s", errors="coerce")
    except (TypeError, ValueError):
        return pd.NaT


def ensure_timestamp_column(frame: pd.DataFrame) -> pd.DataFrame:
    log_step("Ensuring Timestamp column is available")

    if frame.empty:
        frame["Timestamp"] = pd.Series(dtype="datetime64[ns]")
        return frame

    timestamp_source = find_first_existing_column(
        frame,
        ["timestamp", "captured_at", "created_at", "time"],
    )
    path_source = find_first_existing_column(frame, ["file_name", "filename", "image_path", "file"])

    if timestamp_source:
        frame["Timestamp"] = pd.to_datetime(frame[timestamp_source], errors="coerce")
    elif path_source:
        frame["Timestamp"] = frame[path_source].fillna("").map(extract_timestamp_from_path)
    else:
        logging.warning("Timestamp column could not be inferred. Using NaT.")
        frame["Timestamp"] = pd.NaT

    unresolved = frame["Timestamp"].isna().sum()
    if unresolved:
        logging.warning("Timestamp could not be parsed for %s rows", unresolved)

    return frame


def deduplicate_and_sort(frame: pd.DataFrame) -> pd.DataFrame:
    log_step("Removing duplicate records based on Employee and Text, then sorting by Timestamp")

    if frame.empty:
        return frame

    before = len(frame)
    deduped = frame.drop_duplicates(subset=["Employee", "Text"], keep="first").copy()
    after = len(deduped)
    log_step(f"Removed {before - after} duplicate rows")

    deduped["TimestampSort"] = deduped["Timestamp"].fillna(pd.Timestamp.max)
    deduped = deduped.sort_values(by=["TimestampSort", "Employee"], kind="stable").drop(columns=["TimestampSort"])
    deduped.reset_index(drop=True, inplace=True)
    return deduped


def classify_activity(text: str) -> str:
    lowered = str(text or "").lower()

    for group_name, keywords in ACTIVITY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return group_name

    return "other"


def add_activity_group(frame: pd.DataFrame) -> pd.DataFrame:
    log_step("Classifying activities into keyword-based groups")

    if frame.empty:
        frame["ActivityGroup"] = pd.Series(dtype="object")
        return frame

    path_source = find_first_existing_column(frame, ["file_name", "filename", "image_path", "file"])
    search_text = frame["Text"].fillna("").astype(str)

    if path_source:
        search_text = search_text + " " + frame[path_source].fillna("").astype(str)

    frame["ActivityGroup"] = search_text.map(classify_activity)
    return frame


def generate_time_compression(frame: pd.DataFrame) -> pd.DataFrame:
    log_step("Generating time-based compression by employee and activity group")

    columns = ["Employee", "ActivityGroup", "StartTime", "EndTime", "TotalEntries"]
    if frame.empty:
        return pd.DataFrame(columns=columns)

    valid = frame.dropna(subset=["Timestamp"]).copy()
    if valid.empty:
        logging.warning("No valid timestamps found. Time compression will be empty.")
        return pd.DataFrame(columns=columns)

    compressed = (
        valid.groupby(["Employee", "ActivityGroup"], dropna=False)
        .agg(
            StartTime=("Timestamp", "min"),
            EndTime=("Timestamp", "max"),
            TotalEntries=("ActivityGroup", "size"),
        )
        .reset_index()
        .sort_values(by=["Employee", "StartTime", "ActivityGroup"], kind="stable")
    )
    return compressed


def summarize_top_activities(activity_series: pd.Series) -> str:
    counts = activity_series.value_counts().head(3)
    if counts.empty:
        return ""
    return ", ".join(f"{index} ({value})" for index, value in counts.items())


def generate_employee_summary(frame: pd.DataFrame) -> pd.DataFrame:
    log_step("Generating employee-level summary")

    columns = ["Employee", "TotalActivityCount", "Top3Activities"]
    if frame.empty:
        return pd.DataFrame(columns=columns)

    total_counts = (
        frame.groupby("Employee", dropna=False)
        .size()
        .reset_index(name="TotalActivityCount")
    )
    top_activities = (
        frame.groupby("Employee", dropna=False)["ActivityGroup"]
        .agg(summarize_top_activities)
        .reset_index(name="Top3Activities")
    )
    summary = total_counts.merge(top_activities, on="Employee", how="left").sort_values(
        by=["TotalActivityCount", "Employee"],
        ascending=[False, True],
        kind="stable",
    )
    return summary


def save_csv(frame: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    log_step(f"Saved {len(frame)} rows to {output_path}")


def compress_to_gzip(source_path: Path, target_path: Path) -> None:
    log_step(f"Compressing {source_path.name} into {target_path.name}")

    if not source_path.exists():
        logging.warning("Source file for gzip compression does not exist: %s", source_path)
        return

    with source_path.open("rb") as source_file, gzip.open(target_path, "wb") as target_file:
        target_file.writelines(source_file)

    log_step(f"Created gzip archive at {target_path}")


def run_pipeline(input_path: Path = INPUT_FILE) -> None:
    configure_logging()
    log_step("Starting OCR log processing pipeline")

    frame = load_csv(input_path)
    frame = ensure_text_column(frame)
    frame = ensure_employee_column(frame)
    frame = ensure_timestamp_column(frame)

    compressed_logs = deduplicate_and_sort(frame.copy())
    grouped_logs = add_activity_group(compressed_logs.copy())
    time_compressed = generate_time_compression(grouped_logs)
    summary = generate_employee_summary(grouped_logs)

    save_csv(compressed_logs, COMPRESSED_LOGS_FILE)
    save_csv(grouped_logs, GROUPED_LOGS_FILE)
    save_csv(time_compressed, TIME_COMPRESSED_FILE)
    save_csv(summary, SUMMARY_FILE)
    save_csv(grouped_logs, FINAL_CSV_FILE)
    compress_to_gzip(FINAL_CSV_FILE, FINAL_GZIP_FILE)

    log_step("OCR log processing pipeline completed successfully")


if __name__ == "__main__":
    run_pipeline()
