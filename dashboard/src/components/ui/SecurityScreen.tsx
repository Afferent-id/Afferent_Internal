'use client';

import type { ReactNode } from 'react';
import { ShieldCheck } from 'lucide-react';
import Logo from '@/components/Logo';
import ThemeToggle from '@/components/ThemeToggle';
import LanguageSwitch from '@/components/ui/LanguageSwitch';
import '@/app/security-pages.css';

interface SecurityScreenProps {
  /** Small line after the brand name, e.g. "Secure Gateway". */
  area: string;
  /** What this page is, shown as a chip in the top bar. */
  status: string;
  tone: 'blocked' | 'education';
  icon: ReactNode;
  eyebrow: string;
  title: string;
  lead: ReactNode;
  /** Extra content under the lead in the dark story panel (destination, assurance). */
  heroExtra?: ReactNode;
  actions: ReactNode;
  guideEyebrow: string;
  guideTitle: string;
  guideId: string;
  /** Content of the right-hand panel. */
  children: ReactNode;
  footerLeft: string;
  footerRight?: string;
}

/**
 * Two-column enterprise layout for the pages that interrupt a person: a dark story panel on the left
 * (what happened, what to do first) and a guidance panel on the right (what to do next).
 * It stacks into one column on narrow screens. Language and theme stay available in the top bar.
 */
export default function SecurityScreen(props: SecurityScreenProps) {
  const { area, status, tone, icon, eyebrow, title, lead, heroExtra, actions, guideEyebrow, guideTitle, guideId, children, footerLeft, footerRight } = props;
  return (
    <div className="sec-page" data-tone={tone}>
      <div className="sec-workspace">
        <header className="sec-bar">
          <span className="sec-brand"><Logo variant="mark" size={26} />Afferent <span className="brand-reflex">Reflex</span><span className="sec-brand-sep" aria-hidden="true">/</span><small>{area}</small></span>
          <span className="sec-tools">
            <span className="sec-status">{status}</span>
            <LanguageSwitch />
            <ThemeToggle />
          </span>
        </header>
        <main className="sec-shell" id="content">
          <section className="sec-hero" aria-labelledby="sec-title">
            <span className="sec-icon" aria-hidden="true">{icon}</span>
            <span className="sec-eyebrow">{eyebrow}</span>
            <h1 id="sec-title">{title}</h1>
            <p className="sec-lead">{lead}</p>
            {heroExtra}
            <div className="sec-actions">{actions}</div>
          </section>
          <section className="sec-guide" aria-labelledby={guideId}>
            <span className="sec-eyebrow">{guideEyebrow}</span>
            <h2 id={guideId}>{guideTitle}</h2>
            {children}
          </section>
        </main>
        <footer className="sec-foot">
          <span><ShieldCheck size={15} aria-hidden="true" />{footerLeft}</span>
          {footerRight && <span>{footerRight}</span>}
        </footer>
      </div>
    </div>
  );
}
