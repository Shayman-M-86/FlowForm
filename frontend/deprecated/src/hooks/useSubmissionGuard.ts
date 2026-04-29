/**
 * Lightweight browser-side guard that remembers which surveys this browser has
 * already submitted. Stored in localStorage — easy to clear, but a sufficient
 * deterrent against accidental re-submissions.
 *
 * Key format:
 *   "survey_<surveyId>"  — for public-slug submissions
 *   "token_<prefix>"     — for private-link submissions (token prefix, not the full secret)
 */

const STORAGE_KEY = "flowform_submitted";

function readSet(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return new Set(JSON.parse(raw) as string[]);
  } catch {
    // ignore parse errors
  }
  return new Set();
}

function writeSet(s: Set<string>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...s]));
  } catch {
    // ignore quota errors
  }
}

export function hasSubmitted(key: string): boolean {
  return readSet().has(key);
}

export function markSubmitted(key: string): void {
  const s = readSet();
  s.add(key);
  writeSet(s);
}

export function surveyKey(surveyId: number): string {
  return `survey_${surveyId}`;
}

export function tokenKey(tokenPrefix: string): string {
  return `token_${tokenPrefix}`;
}
