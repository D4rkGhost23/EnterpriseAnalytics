"""
Secure file ingestion service with multi-layer validation.
Implements the Malicious File Defense Protocol.
"""
import os
import hashlib
import tempfile
import asyncio
import chardet
import structlog
from pathlib import Path
from typing import Tuple, Dict, Any
import pandas as pd

logger = structlog.get_logger()

# Security constants
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".json"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
SUSPICIOUS_PATTERNS = [
    b"__import__", b"exec(", b"eval(", b"os.system",
    b"subprocess", b"<script", b"javascript:", b"<?php",
    b"powershell", b"cmd.exe", b"\x00\x00\x01\x00",  # PE header fragments
]
# Magic bytes for allowed types
MAGIC_BYTES = {
    b"\xef\xbb\xbf": "csv",        # UTF-8 BOM (CSV)
    b"PK\x03\x04": "xlsx",          # ZIP/XLSX
    b"PK\x05\x06": "xlsx",
    b"\xff\xfe": "csv",              # UTF-16 LE BOM
    b"\xfe\xff": "csv",              # UTF-16 BE BOM
}


class IngestionError(Exception):
    """Raised when file ingestion fails a security check."""
    pass


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_magic_bytes(data: bytes, declared_ext: str) -> bool:
    """
    Verify file type matches declared extension using magic bytes.
    JSON and CSV don't have fixed magic bytes — accept them if content validates.
    """
    if declared_ext == ".xlsx":
        return data[:4] in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
    # CSV / JSON: no magic bytes, validated by content parsing
    return True


def scan_for_malicious_content(data: bytes) -> Tuple[bool, str]:
    """Scan raw bytes for known malicious patterns."""
    lower = data[:8192].lower()  # Check first 8K
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.lower() in lower:
            return True, f"Suspicious pattern detected: {pattern[:20]}"
    return False, ""


def enforce_utf8_encoding(data: bytes, ext: str) -> str:
    """Enforce UTF-8 encoding for CSV/JSON. Reject or convert others."""
    if ext == ".xlsx":
        return "utf-8"  # XLSX is binary, encoding handled by openpyxl
    detected = chardet.detect(data[:8192])
    encoding = detected.get("encoding", "utf-8") or "utf-8"
    confidence = detected.get("confidence", 0)
    # Try decoding as UTF-8
    try:
        data.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        if encoding.upper() in ("ASCII", "UTF-8", "UTF-8-SIG"):
            raise IngestionError("File encoding is not UTF-8 compatible")
        # Try detected encoding as fallback
        try:
            content = data.decode(encoding)
            # Re-encode check
            content.encode("utf-8")
            return encoding
        except Exception:
            raise IngestionError(f"Cannot decode file with encoding {encoding}")


def validate_file_extension(filename: str) -> str:
    """Validate extension is in whitelist, preventing path traversal."""
    safe_name = Path(filename).name  # Strip any directory traversal
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise IngestionError(f"File type '{ext}' is not allowed. Accepted: {ALLOWED_EXTENSIONS}")
    return ext


async def parse_dataframe(data: bytes, ext: str, encoding: str) -> pd.DataFrame:
    """Parse file bytes to DataFrame in executor to avoid blocking."""
    def _parse():
        with tempfile.NamedTemporaryFile(suffix=ext, delete=True) as tmp:
            tmp.write(data)
            tmp.flush()
            if ext == ".csv":
                return pd.read_csv(tmp.name, encoding=encoding, low_memory=False)
            elif ext == ".xlsx":
                return pd.read_excel(tmp.name, engine="openpyxl")
            elif ext == ".json":
                return pd.read_json(tmp.name, encoding=encoding)
            else:
                raise IngestionError("Unsupported file type")

    loop = asyncio.get_event_loop()
    try:
        df = await asyncio.wait_for(loop.run_in_executor(None, _parse), timeout=60.0)
        return df
    except asyncio.TimeoutError:
        raise IngestionError("File processing timed out (60s limit)")
    except Exception as e:
        raise IngestionError(f"Failed to parse file: {str(e)}")


async def ingest_file(
    filename: str,
    file_data: bytes,
    content_type: str,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Full ingestion pipeline with security validation.
    Returns (DataFrame, file_metadata_dict) or raises IngestionError.
    """
    audit = {}

    # 1. File size check
    size = len(file_data)
    if size > MAX_FILE_SIZE_BYTES:
        raise IngestionError(f"File too large: {size} bytes (max {MAX_FILE_SIZE_BYTES})")
    audit["file_size_bytes"] = size

    # 2. Extension validation + path traversal prevention
    ext = validate_file_extension(filename)
    safe_name = Path(filename).name
    audit["file_type"] = ext.lstrip(".")
    audit["safe_filename"] = safe_name

    # 3. SHA-256 hash for audit trail
    file_hash = compute_sha256(file_data)
    audit["file_hash"] = file_hash
    logger.info("file_ingestion_started", filename=safe_name, size=size, hash=file_hash)

    # 4. Magic byte verification for XLSX
    if not check_magic_bytes(file_data, ext):
        logger.warning("mime_mismatch", filename=safe_name, ext=ext)
        raise IngestionError("File content does not match declared extension (MIME mismatch)")

    # 5. Malicious content scan
    is_malicious, reason = scan_for_malicious_content(file_data)
    if is_malicious:
        logger.error("malicious_file_rejected", filename=safe_name, reason=reason, hash=file_hash)
        raise IngestionError(f"File rejected for security reasons: {reason}")

    # 6. Encoding enforcement
    encoding = enforce_utf8_encoding(file_data, ext)
    audit["encoding"] = encoding

    # 7. Parse to DataFrame
    df = await parse_dataframe(file_data, ext, encoding)

    # 8. Basic structural validation
    if df.empty:
        raise IngestionError("Uploaded file contains no data")
    if len(df.columns) == 0:
        raise IngestionError("Uploaded file has no columns")

    audit["row_count"] = len(df)
    audit["column_count"] = len(df.columns)

    logger.info("file_ingestion_success", filename=safe_name, rows=len(df), cols=len(df.columns))
    return df, audit
