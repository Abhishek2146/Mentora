"""
Unit tests for email format + domain (MX) verification helpers.

No live DNS or network required; the resolver is mocked.
"""
from unittest.mock import patch

import pytest

import app.utils.email_validation as ev
from app.utils.email_validation import (
    domain_receives_mail,
    get_email_domain,
    is_valid_email,
    normalize_email,
    verify_email_domain,
)


@pytest.fixture(autouse=True)
def clear_mx_cache():
    ev._MX_CACHE.clear()
    yield
    ev._MX_CACHE.clear()


class TestNormalizeEmail:
    def test_lowercases_and_strips(self):
        assert normalize_email("  Student@Example.Com  ") == "student@example.com"

    def test_empty(self):
        assert normalize_email("") == ""


class TestIsValidEmail:
    def test_common_email_valid(self):
        assert is_valid_email("student@example.com") is True

    def test_lowercased_and_stripped(self):
        assert is_valid_email("  NAME@Domain.COM  ") is True

    def test_plus_tag_and_dot_valid(self):
        assert is_valid_email("user.name+tag@sub.example.co") is True

    def test_missing_at(self):
        assert is_valid_email("notanemail") is False

    def test_missing_domain(self):
        assert is_valid_email("user@") is False

    def test_missing_local_part(self):
        assert is_valid_email("@example.com") is False

    def test_no_tld(self):
        assert is_valid_email("user@domain") is False

    def test_no_dot_in_domain(self):
        assert is_valid_email("user@example") is False

    def test_invalid_tld(self):
        assert is_valid_email("user@example.x") is False

    def test_spaces_inside(self):
        assert is_valid_email("user name@example.com") is False

    def test_multiple_at(self):
        assert is_valid_email("a@b@example.com") is False


class TestGetEmailDomain:
    def test_returns_domain(self):
        assert get_email_domain("a@Google.com") == "google.com"

    def test_malformed_returns_none(self):
        assert get_email_domain("not-an-email") is None


class TestDomainReceivesMail:
    @patch.object(ev, "_check_mx", return_value=True)
    def test_domain_with_mx(self, mock_mx):
        assert domain_receives_mail("gmail.com") is True

    @patch.object(ev, "_check_mx", return_value=False)
    def test_domain_without_mx(self, mock_mx):
        assert domain_receives_mail("no-such-domain.xyz") is False

    @patch.object(ev, "_check_mx", return_value=None)
    def test_transient_lookup_failure_is_neither_true_nor_false(self, mock_mx):
        assert domain_receives_mail("flaky-example.com") is None

    @patch.object(ev, "_check_mx", return_value=True)
    def test_cache_avoids_repeated_lookups(self, mock_mx):
        assert domain_receives_mail("gmail.com") is True
        assert domain_receives_mail("gmail.com") is True
        mock_mx.assert_called_once()

    def test_empty_domain_rejected(self):
        assert domain_receives_mail("") is False


class TestVerifyEmailDomain:
    @patch.object(ev, "domain_receives_mail", return_value=True)
    def test_real_domain_ok(self, mock_mail):
        assert verify_email_domain("user@gmail.com") is None

    @patch.object(ev, "domain_receives_mail", return_value=False)
    def test_fake_domain_rejected(self, mock_mail):
        error = verify_email_domain("user@no-such-domain.xyz")
        assert error is not None
        assert "no-such-domain.xyz" in error

    @patch.object(ev, "domain_receives_mail", return_value=None)
    def test_transient_failure_fails_open(self, mock_mail):
        assert verify_email_domain("user@flaky-example.com") is None

    def test_malformed_email_rejected(self):
        assert verify_email_domain("not-an-email") is not None