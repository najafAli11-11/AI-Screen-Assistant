export const API_URL = import.meta.env.VITE_API_URL ?? window.location.origin;

export const LANGUAGES = [
  { code: 'ur', label: 'Urdu', nativeName: 'اردو' },
  { code: 'en', label: 'English', nativeName: 'English' },
  { code: 'hi', label: 'Hindi', nativeName: 'हिन्दी' },
] as const;

export type LanguageCode = (typeof LANGUAGES)[number]['code'];
