'use client';

import type { ReactNode } from 'react';
import StateMessage from '@/components/ui/StateMessage';
import { useI18n } from '@/i18n/I18nProvider';
import type { LoadState } from '@/lib/loadState';
import type { MessageKey } from '@/i18n/messages';

interface LoadGateProps {
  state?: LoadState;
  /** What failed, in one sentence ("We could not load accounts."). Falls back to a general sentence. */
  errorTitle?: MessageKey;
  lines?: number;
  compact?: boolean;
  children: ReactNode;
}

/** Shows a skeleton while the first answer is on its way, a retryable error when it failed, and the content otherwise. */
export default function LoadGate({ state, errorTitle, lines = 4, compact, children }: LoadGateProps) {
  const { t } = useI18n();
  if (state?.status === 'loading') return <StateMessage variant="loading" lines={lines} compact={compact} />;
  if (state?.status === 'error') {
    return <StateMessage variant="error" compact={compact} title={errorTitle ? t(errorTitle) : undefined} action={state.retry ? { label: t('common.retry'), onClick: state.retry } : undefined} />;
  }
  return <>{children}</>;
}
