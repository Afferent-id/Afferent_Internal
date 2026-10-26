'use client';

import { useI18n } from '@/i18n/I18nProvider';
import type { MessageKey } from '@/i18n/messages';

export type EducationDelivery = {
  sent_at: string | null;
  last_error: string | null;
  kind?: 'training' | 'baseline';
  actor_role?: string | null;
};

/** Both inboxes describe the same persisted email outcome. */
export default function NotificationDelivery({ delivery }: { delivery: EducationDelivery | null }) {
  const { t } = useI18n();
  const text = !delivery ? t('inbox.emp.none')
    : delivery.last_error === 'skipped_not_eligible' ? t('inbox.emp.cancelled')
    : delivery.sent_at ? t('inbox.emp.sent', { time: delivery.sent_at })
    : delivery.last_error ? t('inbox.emp.retry') : t('inbox.emp.queued');
  const role = delivery?.actor_role;
  return <span title={text}>{text}{delivery?.kind && <small className="cell-sub">
    {t(delivery.kind === 'training' ? 'inbox.delivery.training' : 'inbox.delivery.baseline')}
    {role && ['soc', 'phishing_admin'].includes(role) && <> · {t(`role.${role}` as MessageKey)}</>}
  </small>}</span>;
}
