import pytest
import os
from datetime import date, datetime, timezone, timedelta
from unittest.mock import patch, Mock
from cryptography.fernet import Fernet, InvalidToken

from src.api.common.utils.datetime import (
    get_current_datetime,
    get_date,
    get_month_boundaries,
    get_month_start,
    get_month_end
)
from src.api.common.utils.encryption import encrypt_data, decrypt_data
from src.api.common.utils.database import (
    get_database_url,
    _get_database_url_from_env_vars
)


class TestDatetimeUtils:
    """Test datetime utility functions"""

    def test_get_current_datetime_returns_utc_with_timezone(self):
        """Test that get_current_datetime returns UTC datetime with timezone info"""
        result = get_current_datetime()
        
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc
        assert result.microsecond == 0  # Should be stripped for consistency

    def test_get_current_datetime_consistency(self):
        """Test that get_current_datetime returns consistent format"""
        result1 = get_current_datetime()
        result2 = get_current_datetime()
        
        # Should be very close in time (within 1 second)
        time_diff = abs((result2 - result1).total_seconds())
        assert time_diff < 1.0

    def test_get_date_with_valid_string(self):
        """Test get_date with valid ISO date string"""
        date_str = "2024-01-15"
        result = get_date(date_str)
        
        assert result == date(2024, 1, 15)

    def test_get_date_with_datetime_string(self):
        """Test get_date with datetime string (should extract date part)"""
        date_str = "2024-01-15T10:30:00Z"
        result = get_date(date_str)
        
        assert result == date(2024, 1, 15)

    def test_get_date_with_none(self):
        """Test get_date with None input"""
        result = get_date(None)
        assert result is None

    def test_get_date_with_empty_string(self):
        """Test get_date with empty string"""
        with pytest.raises(ValueError):
            get_date("")

    def test_get_date_with_invalid_format(self):
        """Test get_date with invalid date format"""
        with pytest.raises(ValueError):
            get_date("invalid-date")

    def test_get_month_boundaries_regular_month(self):
        """Test get_month_boundaries for a regular month"""
        target_month = date(2024, 6, 15)
        start, end = get_month_boundaries(target_month)
        
        assert start == date(2024, 6, 1)
        assert end == date(2024, 6, 30)

    def test_get_month_boundaries_december(self):
        """Test get_month_boundaries for December (year boundary)"""
        target_month = date(2024, 12, 15)
        start, end = get_month_boundaries(target_month)
        
        assert start == date(2024, 12, 1)
        assert end == date(2024, 12, 31)

    def test_get_month_boundaries_february_leap_year(self):
        """Test get_month_boundaries for February in leap year"""
        target_month = date(2024, 2, 15)  # 2024 is a leap year
        start, end = get_month_boundaries(target_month)
        
        assert start == date(2024, 2, 1)
        assert end == date(2024, 2, 29)

    def test_get_month_boundaries_february_non_leap_year(self):
        """Test get_month_boundaries for February in non-leap year"""
        target_month = date(2023, 2, 15)  # 2023 is not a leap year
        start, end = get_month_boundaries(target_month)
        
        assert start == date(2023, 2, 1)
        assert end == date(2023, 2, 28)

    def test_get_month_start(self):
        """Test get_month_start function"""
        target_month = date(2024, 6, 15)
        result = get_month_start(target_month)
        
        assert result == date(2024, 6, 1)

    def test_get_month_start_first_day(self):
        """Test get_month_start when input is already first day"""
        target_month = date(2024, 6, 1)
        result = get_month_start(target_month)
        
        assert result == date(2024, 6, 1)

    def test_get_month_end_regular_month(self):
        """Test get_month_end for regular month"""
        target_month = date(2024, 6, 15)
        result = get_month_end(target_month)
        
        assert result == date(2024, 6, 30)

    def test_get_month_end_december(self):
        """Test get_month_end for December"""
        target_month = date(2024, 12, 15)
        result = get_month_end(target_month)
        
        assert result == date(2024, 12, 31)

    def test_get_month_end_last_day(self):
        """Test get_month_end when input is already last day"""
        target_month = date(2024, 6, 30)
        result = get_month_end(target_month)
        
        assert result == date(2024, 6, 30)


class TestEncryptionUtils:
    """Test encryption utility functions"""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption work together"""
        original_data = "sensitive information"
        
        encrypted = encrypt_data(original_data)
        decrypted = decrypt_data(encrypted)
        
        assert decrypted == original_data
        assert encrypted != original_data  # Should be different when encrypted

    def test_encrypt_empty_string(self):
        """Test encrypting empty string"""
        result = encrypt_data("")
        assert result == ""

    def test_decrypt_empty_string(self):
        """Test decrypting empty string"""
        result = decrypt_data("")
        assert result == ""

    def test_encrypt_none_value(self):
        """Test encrypting None value (should handle gracefully)"""
        # Test that None values are handled appropriately
        result = encrypt_data(None)
        # Should return None or empty string depending on implementation
        assert result is None or result == ""

    def test_encrypt_unicode_data(self):
        """Test encrypting unicode data"""
        unicode_data = "Héllo Wörld! 🌍"
        
        encrypted = encrypt_data(unicode_data)
        decrypted = decrypt_data(encrypted)
        
        assert decrypted == unicode_data

    def test_encrypt_long_data(self):
        """Test encrypting long data"""
        long_data = "x" * 10000
        
        encrypted = encrypt_data(long_data)
        decrypted = decrypt_data(encrypted)
        
        assert decrypted == long_data

    def test_decrypt_invalid_data(self):
        """Test decrypting invalid encrypted data"""
        with pytest.raises(InvalidToken):
            decrypt_data("invalid-encrypted-data")

    def test_decrypt_corrupted_data(self):
        """Test decrypting corrupted encrypted data"""
        original_data = "test data"
        encrypted = encrypt_data(original_data)
        
        # Corrupt the encrypted data
        corrupted = encrypted[:-5] + "xxxxx"
        
        with pytest.raises(InvalidToken):
            decrypt_data(corrupted)

    def test_encryption_consistency(self):
        """Test that same data encrypts to different values (due to randomness)"""
        data = "test data"
        
        encrypted1 = encrypt_data(data)
        encrypted2 = encrypt_data(data)
        
        # Should be different due to random IV/nonce
        assert encrypted1 != encrypted2
        
        # But both should decrypt to same value
        assert decrypt_data(encrypted1) == data
        assert decrypt_data(encrypted2) == data


class TestDatabaseUtils:
    """Test database utility functions"""

    def test_get_database_url_from_env_vars_default(self):
        """Test _get_database_url_from_env_vars with default values"""
        with patch.dict(os.environ, {}, clear=True):
            result = _get_database_url_from_env_vars()
            expected = "postgresql://postgres:postgres@db:5432/assessments"
            assert result == expected

    def test_get_database_url_from_env_vars_custom(self):
        """Test _get_database_url_from_env_vars with custom values"""
        env_vars = {
            "DB_SCHEME": "mysql",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_HOST": "localhost",
            "DB_PORT": "3306",
            "DB_NAME": "testdb"
        }
        
        with patch.dict(os.environ, env_vars):
            result = _get_database_url_from_env_vars()
            expected = "mysql://testuser:testpass@localhost:3306/testdb"
            assert result == expected

    def test_get_database_url_from_env_vars_partial(self):
        """Test _get_database_url_from_env_vars with partial custom values"""
        env_vars = {
            "DB_USER": "customuser",
            "DB_NAME": "customdb"
        }
        
        with patch.dict(os.environ, env_vars):
            result = _get_database_url_from_env_vars()
            expected = "postgresql://customuser:postgres@db:5432/customdb"
            assert result == expected

    def test_get_database_url_with_database_url_env(self):
        """Test get_database_url when DATABASE_URL is set"""
        custom_url = "postgresql://user:pass@host:5432/db"
        
        with patch.dict(os.environ, {"DATABASE_URL": custom_url}):
            result = get_database_url()
            assert result == custom_url

    def test_get_database_url_without_database_url_env(self):
        """Test get_database_url when DATABASE_URL is not set"""
        env_vars = {
            "DB_USER": "testuser",
            "DB_NAME": "testdb"
        }
        
        # Remove DATABASE_URL if it exists and set other vars
        with patch.dict(os.environ, env_vars):
            if "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]
            
            result = get_database_url()
            expected = "postgresql://testuser:postgres@db:5432/testdb"
            assert result == expected

    def test_get_database_url_empty_database_url_env(self):
        """Test get_database_url when DATABASE_URL is empty"""
        env_vars = {
            "DATABASE_URL": "",
            "DB_USER": "testuser",
            "DB_NAME": "testdb"
        }
        
        with patch.dict(os.environ, env_vars):
            result = get_database_url()
            # Should return empty string when DATABASE_URL is explicitly empty
            assert result == ""

    def test_database_url_special_characters(self):
        """Test database URL construction with special characters in password"""
        env_vars = {
            "DB_USER": "user@domain",
            "DB_PASSWORD": "pass@word#123",
            "DB_HOST": "db-host.com"
        }
        
        with patch.dict(os.environ, env_vars):
            result = _get_database_url_from_env_vars()
            expected = "postgresql://user@domain:pass@word#123@db-host.com:5432/devengo"
            assert result == expected

    @patch('src.api.common.utils.database.Session')
    @patch('src.api.common.utils.database.engine')
    def test_get_db_generator(self, mock_engine, mock_session_class):
        """Test get_db generator function"""
        from src.api.common.utils.database import get_db
        
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        # Test the generator
        db_gen = get_db()
        db_session = next(db_gen)
        
        assert db_session == mock_session
        mock_session_class.assert_called_once_with(mock_engine)

    def test_engine_configuration(self):
        """Test that engine is configured correctly"""
        from src.api.common.utils.database import engine
        
        assert engine is not None
        # In test environment, echo should be True (since ENV != "production")
        assert engine.echo is True 