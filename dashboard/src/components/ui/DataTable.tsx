'use client';

import { useMemo, useState, type KeyboardEvent, type ReactNode } from 'react';
import { useScrollCue } from '@/hooks/useScrollCue';
import { ArrowDown, ArrowUp } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  /** Provide to make the column sortable. */
  sortValue?: (row: T) => string | number;
  align?: 'left' | 'right';
  /** Hide this column in narrow containers. */
  secondary?: boolean;
  /** Hide this column only in very narrow containers (phones); the page keeps the key columns without sideways scrolling. */
  low?: boolean;
}

interface DataTableProps<T> {
  /** Names the table for screen readers. */
  caption: string;
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  selectedKey?: string | null;
  density?: 'compact' | 'comfortable';
  empty?: ReactNode;
  /** Keep large SOC lists readable while retaining every row. */
  pageSize?: number;
}

/** One table for incidents, traffic, accounts, campaigns and clauses. */
export default function DataTable<T>({ caption, columns, rows, rowKey, onRowClick, selectedKey, density = 'compact', empty, pageSize }: DataTableProps<T>) {
  const { t } = useI18n();
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<{ key: string; dir: 'asc' | 'desc' } | null>(null);
  const [wrap, more] = useScrollCue(`${rows.length}:${columns.length}`);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const column = columns.find(c => c.key === sort.key);
    if (!column?.sortValue) return rows;
    const get = column.sortValue;
    return [...rows].sort((a, b) => {
      const x = get(a); const y = get(b);
      const result = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y));
      return sort.dir === 'asc' ? result : -result;
    });
  }, [rows, columns, sort]);

  const toggle = (key: string) => {
    setPage(0);
    setSort(current => (current?.key === key ? (current.dir === 'asc' ? { key, dir: 'desc' } : null) : { key, dir: 'asc' }));
  };
  const size = pageSize ? Math.max(1, Math.floor(pageSize)) : sorted.length || 1;
  const pages = Math.max(1, Math.ceil(sorted.length / size));
  const current = Math.min(page, pages - 1);
  // A resolved/removed last row must not leave a hidden page that reappears later.
  if (page !== current) setPage(current);
  const start = current * size;
  const visibleRows = pageSize ? sorted.slice(start, start + size) : sorted;
  const onKey = (event: KeyboardEvent<HTMLTableRowElement>, row: T) => {
    if (!onRowClick) return;
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onRowClick(row); }
  };

  if (rows.length === 0 && empty) return <>{empty}</>;
  return (
    <div className="data-table-panel">
    <div ref={wrap} className="table-wrap" data-density={density} data-more={more || undefined} role="region" aria-label={caption} tabIndex={0}>
      <table className="data-table">
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            {columns.map(column => {
              const active = sort?.key === column.key;
              return (
                <th key={column.key} scope="col" data-align={column.align} data-secondary={column.secondary || undefined} data-low={column.low || undefined} aria-sort={active ? (sort?.dir === 'asc' ? 'ascending' : 'descending') : column.sortValue ? 'none' : undefined}>
                  {column.sortValue
                    ? <button type="button" className="th-sort" onClick={() => toggle(column.key)}>{column.header}{active && (sort?.dir === 'asc' ? <ArrowUp size={12} aria-hidden="true" /> : <ArrowDown size={12} aria-hidden="true" />)}</button>
                    : column.header}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {visibleRows.map(row => {
            const key = rowKey(row);
            return (
              <tr key={key} data-clickable={onRowClick ? '' : undefined} aria-selected={onRowClick ? selectedKey === key : undefined} tabIndex={onRowClick ? 0 : undefined} onClick={onRowClick ? () => onRowClick(row) : undefined} onKeyDown={event => onKey(event, row)}>
                {columns.map(column => <td key={column.key} data-align={column.align} data-secondary={column.secondary || undefined} data-low={column.low || undefined}>{column.render(row)}</td>)}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
    {pageSize && <nav className="table-pagination" aria-label={t('table.navigation', { name: caption })}>
      <span>{t('table.range', { from: start + 1, to: Math.min(start + size, rows.length), total: rows.length })}</span>
      <div><button type="button" className="btn" disabled={current === 0} onClick={() => setPage(current - 1)}>{t('table.previous')}</button><span>{t('table.page', { page: current + 1, pages })}</span><button type="button" className="btn" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}>{t('table.next')}</button></div>
    </nav>}
    </div>
  );
}
