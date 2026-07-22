// Normalise the base URL: strip any trailing slash(es) so that
// `${API_URL}/api/token` can never become `…app//api/token`, which the backend
// rejects with a 404 "Not Found". This makes VITE_API_URL tolerant of a
// trailing slash in the Railway variable.
const rawApiUrl = import.meta.env.VITE_API_URL ?? window.location.origin;
export const API_URL = rawApiUrl.replace(/\/+$/, '');

export const LANGUAGES = [
  { code: 'ur', label: 'Urdu', nativeName: 'اردو' },
  { code: 'en', label: 'English', nativeName: 'English' },
  { code: 'hi', label: 'Hindi', nativeName: 'हिन्दी' },
] as const;

export type LanguageCode = (typeof LANGUAGES)[number]['code'];
