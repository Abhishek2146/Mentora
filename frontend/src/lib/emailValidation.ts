// Frontend mirror of the backend email format validation. Used for instant
// UX feedback so users don't need to submit to see a format error.

export function normalizeEmail(email: string): string {
  return (email || "").trim().toLowerCase();
}

const EMAIL_REGEX = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

export function isValidEmail(email: string): boolean {
  const normalized = normalizeEmail(email);
  const localPart = normalized.split("@")[0] || "";
  return !normalized.includes("..") && !localPart.startsWith(".") && !localPart.endsWith(".") && EMAIL_REGEX.test(normalized);
}

export function isGmailAddress(email: string): boolean {
  const normalized = normalizeEmail(email);
  const atIndex = normalized.lastIndexOf("@");
  return isValidEmail(normalized) && atIndex > 0 && normalized.slice(atIndex + 1) === "gmail.com";
}
