'use client';

import { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { useI18n } from '@/i18n/I18nProvider';
import LoadGate from '@/components/ui/LoadGate';
import type { LoadState } from '@/lib/loadState';

export interface DonutDataItem {
  name: string;
  value: number;
  color: string;
  /** A different shape per series, so the legend never relies on colour alone. */
  shape?: 'circle' | 'triangle' | 'diamond' | 'square';
  borderColor?: string;
  share?: string;
}

export interface TremorDonutCardProps {
  title: string;
  description?: string;
  data: DonutDataItem[];
  totalLabel?: string;
  unit?: string;
  className?: string;
  state?: LoadState;
}

function Marker({ color, shape = 'circle' }: { color: string; shape?: DonutDataItem['shape'] }) {
  const d = { circle: 'M6 .5a5.5 5.5 0 100 11 5.5 5.5 0 000-11z', triangle: 'M6 .8l5.6 10H.4z', diamond: 'M6 .6L11.4 6 6 11.4.6 6z', square: 'M1 1h10v10H1z' }[shape];
  return <svg className="donut-marker" viewBox="0 0 12 12" width="12" height="12" aria-hidden="true" focusable="false"><path d={d} fill={color} /></svg>;
}

/** A donut with a legend that carries the numbers, so no value is shown by colour alone. */
export function TremorDonutCard({ title, description, data, totalLabel, unit, className = '', state }: TremorDonutCardProps) {
  const { t } = useI18n();
  const [active, setActive] = useState<number | null>(null);
  const total = data.reduce((sum, item) => sum + item.value, 0);
  const share = (value: number) => (total > 0 ? `${Math.round((value / total) * 100)}%` : '0%');

  return (
    <section className={`exec-card ${className}`.trim()} aria-label={title}>
      <div>
        <h3>{title}</h3>
        {description && <p className="emp-muted">{description}</p>}
      </div>
      <LoadGate state={state} errorTitle="err.incidents" lines={3}>
      {total === 0 ? <p className="emp-muted">{t('ov.donut.empty')}</p> : (
        <div className="donut-row">
          <div className="donut-visual">
          <div className="donut-chart" aria-hidden="true">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart accessibilityLayer={false}>
                <Pie rootTabIndex={-1} data={data} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="92%" paddingAngle={2} stroke="var(--bg-surface)" onMouseEnter={(_, index) => setActive(index)} onMouseLeave={() => setActive(null)} isAnimationActive={false}>
                  {data.map((item, index) => <Cell key={item.name} fill={item.color} opacity={active === null || active === index ? 1 : 0.5} />)}
                </Pie>
                <Tooltip itemStyle={{ color: 'var(--text-primary)' }} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="donut-center"><b>{total}</b></div>
          </div>
          <p className="donut-caption"><span className="visually-hidden">{total} </span>{totalLabel ?? t('ov.sev.total')}</p>
          </div>
          <ul className="donut-legend">
            {data.map(item => (
              <li key={item.name}>
                <Marker color={item.color} shape={item.shape} />
                <span>{item.name}</span>
                <b>{item.value}{unit ? ` ${unit}` : ''}</b>
                <small>{share(item.value)}</small>
              </li>
            ))}
          </ul>
        </div>
      )}
      </LoadGate>
    </section>
  );
}

export default TremorDonutCard;
