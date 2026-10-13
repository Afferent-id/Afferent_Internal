'use client';

import Link from 'next/link';
import { ArrowRight, Flag, Link2, LockKeyhole, ShieldAlert } from 'lucide-react';
import SecurityScreen from '@/components/ui/SecurityScreen';
import { useI18n } from '@/i18n/I18nProvider';

/** Where a person lands after clicking a simulated phishing link: calm, specific, and useful. */
export default function SimulationEducation() {
  const { t } = useI18n();
  const habits = [
    { Icon: ShieldAlert, title: t('edu.h1.title'), body: t('edu.h1.body') },
    { Icon: Link2, title: t('edu.h2.title'), body: t('edu.h2.body') },
    { Icon: Flag, title: t('edu.h3.title'), body: t('edu.h3.body') },
  ];
  return (
    <SecurityScreen
      tone="education" area={t('edu.area')} status={t('edu.status')}
      icon={<ShieldAlert size={36} strokeWidth={1.6} />}
      eyebrow={t('edu.eyebrow')} title={t('edu.title')} lead={t('edu.lead')}
      heroExtra={<div className="sec-assure"><LockKeyhole size={20} aria-hidden="true" /><div><strong>{t('edu.assure.title')}</strong><p>{t('edu.assure.body')}</p></div></div>}
      actions={<Link className="btn btn-light" href="/">{t('edu.back')} <ArrowRight size={16} aria-hidden="true" /></Link>}
      guideEyebrow={t('edu.remember')} guideTitle={t('edu.habits')} guideId="education-next"
      footerLeft={t('edu.footer')} footerRight={t('edu.footerNote')}
    >
      <ol className="sec-steps">
        {habits.map(({ Icon, title, body }, index) => (
          <li key={title}><span className="sec-step-icon" aria-hidden="true"><Icon size={20} /></span><div><small>0{index + 1}</small><h3>{title}</h3><p>{body}</p></div></li>
        ))}
      </ol>
      <div className="sec-note"><strong>{t('edu.bookmark.title')}</strong><p>{t('edu.bookmark.body')}</p></div>
    </SecurityScreen>
  );
}
