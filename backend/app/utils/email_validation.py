"""
Email validation helpers.

These helpers enforce that an email is well-formed (syntax) and, for
registration, that its domain actually receives mail (has MX records), so
placeholder/fake addresses like ``test@no-such-domain.xyz`` are rejected.

Fake test emails such as ``test@test.com`` are *not* caught by DNS alone
because the domain is real - blocking those requires an additional
disposable-domain blocklist.
"""

from __future__ import annotations

import re
import time

import dns.exception
import dns.resolver

# A pragmatic, widely-used pattern for a "proper" email address:
#   local-part  -> letters/digits plus . _ % + - (at least one char)
#   @
#   domain      -> letters/digits/dots/hyphens with a TLD of >= 2 letters
# The full RFC 5322 grammar is handled upstream by email-validator (EmailStr);
# this regex is a secondary guard that lets us surface a friendly message and
# rejects things like "@gmail.com", "user@", "user@domain" (no TLD) etc.
EMAIL_REGEX = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
)

# Small in-process cache for MX lookups: domain -> (checked_at, status).
# Status is True (has MX), False (definitively no MX/NXDOMAIN) or
# None (could not be verified - fail open, do not reject on transient DNS
# failures so a resolver hiccup never locks out legitimate users).
_MX_CACHE: dict[str, tuple[float, bool | None]] = {}
_MX_CACHE_TTL_SECONDS = 3600

_RESOLVER = dns.resolver.Resolver()


def normalize_email(email: str) -> str:
    """Lowercase and strip an email address for canonical storage."""
    return (email or "").strip().lower()


def is_valid_email(email: str) -> bool:
    """Return True when the email has a proper, well-formed structure."""
    return bool(EMAIL_REGEX.fullmatch(normalize_email(email)))


def get_email_domain(email: str) -> str | None:
    """Extract the domain part of a normalized email, or None if malformed."""
    parts = normalize_email(email).rsplit("@", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[1]


GMAIL_DOMAIN = "gmail.com"


def is_gmail_address(email: str) -> bool:
    """Return True only for syntactically valid ``@gmail.com`` addresses."""
    return is_valid_email(email) and get_email_domain(email) == GMAIL_DOMAIN


def _check_mx(domain: str) -> bool | None:
    """
    Return True if the domain has at least one MX record, False if it
    definitively does not (NXDOMAIN / no MX answer), or None when the
    lookup could not complete (transient DNS/resolver failure).
    """
    try:
        answers = _RESOLVER.resolve(domain, "MX")
        return len(answers) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return False
    except dns.exception.DNSException:
        # Transient: timeout, no nameservers, network down, etc.
        return None


def domain_receives_mail(domain: str, *, use_cache: bool = True) -> bool | None:
    """Return tri-state MX status for a domain, with a short TTL cache."""
    domain = (domain or "").strip().lower().rstrip(".")
    if not domain:
        return False

    now = time.monotonic()
    if use_cache:
        cached = _MX_CACHE.get(domain)
        if cached is not None and now - cached[0] < _MX_CACHE_TTL_SECONDS:
            return cached[1]

    status = _check_mx(domain)
    if use_cache:
        _MX_CACHE[domain] = (time.monotonic(), status)
    return status


def verify_email_domain(email: str) -> str | None:
    """
    Return an error message when the email's domain does not receive mail.

    Returns ``None`` when the address is acceptable: the domain either has
    an MX record or could not be verified (fail-open on transient errors).
    """
    domain = get_email_domain(email)
    if domain is None:
        return "Please provide a proper, valid email address"
    status = domain_receives_mail(domain)
    if status is False:
        return (
            f"The email domain '@{domain}' does not appear to be a real "
            "mail domain (no MX record found)."
        )
    return None


def verify_gmail_address(email: str) -> str | None:
    """Validate an address for account registration.

    Registration is intentionally limited to Gmail addresses.  The domain
    check happens before the MX lookup so a non-Gmail address gets a clear,
    deterministic validation message rather than a generic DNS error.
    """
    normalized = normalize_email(email)
    if not is_valid_email(normalized):
        return "Please provide a proper, valid Gmail address"
    if get_email_domain(normalized) != GMAIL_DOMAIN:
        return "Only Gmail addresses ending in @gmail.com are accepted for registration."
    return verify_email_domain(normalized)
