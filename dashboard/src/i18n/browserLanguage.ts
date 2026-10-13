import { LANGUAGES, type Language } from '@/i18n/messages';

/** The first language the browser lists that we translate; English when none matches. */
export function pickBrowserLanguage(preferred: readonly string[] | undefined): Language {
  for (const tag of preferred ?? []) {
    const base = tag.toLowerCase().split('-')[0];
    if ((LANGUAGES as string[]).includes(base)) return base as Language;
  }
  return 'en';
}
