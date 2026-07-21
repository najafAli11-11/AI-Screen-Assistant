export function readSessionValue(key: string): string {
  try {
    return window.sessionStorage.getItem(key) ?? '';
  } catch {
    return '';
  }
}

export function writeSessionValue(key: string, value: string): void {
  try {
    window.sessionStorage.setItem(key, value);
  } catch {
    // Storage may be unavailable in hardened browser modes; the app still works without persistence.
  }
}

export function removeSessionValue(key: string): void {
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // Ignore unavailable storage.
  }
}
