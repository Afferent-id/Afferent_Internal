'use client';

import { useRef, type KeyboardEvent } from 'react';

export interface TabItem { id: string; label: string; /** Number of items that need attention; shown as a badge when above zero. */ badge?: number; badgeLabel?: string }

interface TabsProps {
  /** Names the group of tabs for screen readers. */
  label: string;
  tabs: TabItem[];
  selected: string;
  onSelect: (id: string) => void;
  /** Prefix for element ids: tab `x` gets `${idPrefix}-tab-x`, its panel should be `${idPrefix}-panel-x`. */
  idPrefix: string;
}

export const tabId = (prefix: string, id: string) => `${prefix}-tab-${id}`;
export const panelId = (prefix: string, id: string) => `${prefix}-panel-${id}`;

/** Next tab for a key press; null when the key is not one of ours. Wraps at both ends. */
export function nextTab(ids: readonly string[], current: string, key: string): string | null {
  const index = Math.max(0, ids.indexOf(current));
  if (key === 'ArrowRight') return ids[(index + 1) % ids.length];
  if (key === 'ArrowLeft') return ids[(index - 1 + ids.length) % ids.length];
  if (key === 'Home') return ids[0];
  if (key === 'End') return ids[ids.length - 1];
  return null;
}

/**
 * WAI-ARIA tabs with automatic activation: arrow keys move focus and show the panel, Home and End jump to the ends,
 * and only the selected tab is in the Tab order, so the keyboard never gets stuck inside the row.
 */
export default function Tabs({ label, tabs, selected, onSelect, idPrefix }: TabsProps) {
  const refs = useRef(new Map<string, HTMLButtonElement>());
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const target = nextTab(tabs.map(tab => tab.id), selected, event.key);
    if (!target) return;
    event.preventDefault();
    onSelect(target);
    refs.current.get(target)?.focus();
  };
  return (
    <div className="tabs" role="tablist" aria-label={label} onKeyDown={onKeyDown}>
      {tabs.map(tab => (
        <button
          key={tab.id} type="button" role="tab" id={tabId(idPrefix, tab.id)}
          ref={node => { if (node) refs.current.set(tab.id, node); else refs.current.delete(tab.id); }}
          aria-selected={selected === tab.id} aria-controls={panelId(idPrefix, tab.id)} tabIndex={selected === tab.id ? 0 : -1}
          onClick={() => onSelect(tab.id)}
        >
          <span className="tab-label">{tab.label}</span>
          {tab.badge !== undefined && tab.badge > 0 && (
            <span className="tab-badge">
              <span aria-hidden="true">{tab.badge > 99 ? '99+' : tab.badge}</span>
              <span className="visually-hidden">{tab.badgeLabel ?? String(tab.badge)}</span>
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
