'use client';

import { useCallback, useEffect, useSyncExternalStore } from 'react';
import { usePreference } from '@/hooks/usePreference';

export type Theme = 'light' | 'dark';
/** Same key the previous ThemeToggle used, so saved choices carry over. */
export const THEME_KEY = 'hfl_theme';

const DARK_QUERY = '(prefers-color-scheme: dark)';

function subscribeSystem(notify: () => void) {
  const query = window.matchMedia(DARK_QUERY);
  query.addEventListener('change', notify);
  return () => query.removeEventListener('change', notify);
}

/**
 * An explicit choice ('light' or 'dark') always wins. With no saved choice the theme
 * follows the operating system and updates when the system setting changes.
 */
export function useTheme(): [Theme, () => void] {
  const [stored, setStored] = usePreference(THEME_KEY, '');
  const systemDark = useSyncExternalStore(subscribeSystem, () => window.matchMedia(DARK_QUERY).matches, () => false);
  const theme: Theme = stored === 'dark' || stored === 'light' ? stored : systemDark ? 'dark' : 'light';
  useEffect(() => { document.documentElement.setAttribute('data-theme', theme); }, [theme]);
  const toggle = useCallback(() => setStored(theme === 'dark' ? 'light' : 'dark'), [theme, setStored]);
  return [theme, toggle];
}
