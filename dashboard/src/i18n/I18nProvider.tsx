'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore, type ReactNode } from 'react';
import { usePreference } from '@/hooks/usePreference';
import { LANGUAGES, MESSAGES, type Language, type MessageKey } from '@/i18n/messages';
import { pickBrowserLanguage } from '@/i18n/browserLanguage';

export const LANGUAGE_KEY = 'afferent_lang';

type Vars = Record<string, string | number>;
type Translate = (key: MessageKey, vars?: Vars) => string;

interface I18nValue {
  lang: Language;
  setLang: (lang: Language) => void;
  t: Translate;
}

function format(template: string, vars?: Vars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) => (name in vars ? String(vars[name]) : match));
}

const noSubscribe = () => () => {};
const browserLanguage = () => pickBrowserLanguage(navigator.languages?.length ? navigator.languages : [navigator.language]);

const translateEnglish: Translate = (key, vars) => format(MESSAGES.en[key], vars);
const I18nContext = createContext<I18nValue>({ lang: 'en', setLang: () => {}, t: translateEnglish });

export function I18nProvider({ children }: { children: ReactNode }) {
  const [stored, setStored] = usePreference(LANGUAGE_KEY, '');
  // With no saved choice (a first visit, the sign-in page) the browser's language decides, with English as the fallback.
  const detected = useSyncExternalStore(noSubscribe, browserLanguage, () => 'en' as Language);
  const lang: Language = (LANGUAGES as string[]).includes(stored) ? (stored as Language) : detected;

  useEffect(() => { document.documentElement.lang = lang; }, [lang]);

  const t = useCallback<Translate>((key, vars) => format(MESSAGES[lang][key] ?? MESSAGES.en[key], vars), [lang]);
  const value = useMemo<I18nValue>(() => ({ lang, setLang: next => setStored(next), t }), [lang, setStored, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export const useI18n = () => useContext(I18nContext);
