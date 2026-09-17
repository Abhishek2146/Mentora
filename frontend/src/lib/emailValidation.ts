// Frontend mirror of the backend email format validation. Used for instant
// UX feedback so users don't need to submit to see a format error.

export function normalizeEmail(email: string): string {
  return (email || "").trim().toLowerCase();
}

const EMAIL_REGEX = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

export function isValidEmail(email: string): boolean {
  return EMAIL_REGEX.test(normalizeEmail(email));
}

export function isGmailAddress(email: string): boolean {
  const normalized = normalizeEmail(email);
  const atIndex = normalized.lastIndexOf("@");
  return isValidEmail(normalized) && atIndex > 0 && normalized.slice(atIndex + 1) === "gmail.com";
}
