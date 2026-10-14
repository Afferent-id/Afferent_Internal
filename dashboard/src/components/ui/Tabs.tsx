'use client';

import { useEffect, useRef, type KeyboardEvent } from 'react';
import { useScrollCue } from '@/hooks/useScrollCue';

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
  // When the row is wider than its box (phones), the cut edge fades out so it is clear that it can be scrolled.
  const [row, more] = useScrollCue(tabs.length);
  // Keep the selected tab inside the visible part of a scrolling row (a link such as ?view=audit can select the last tab).
  useEffect(() => {
    const ensureVisible = () => {
      const box = row.current; const tab = refs.current.get(selected);
      if (!box || !tab) return;
      // Position of the tab inside the scrolling content (offsetLeft would be relative to a different ancestor).
      const start = tab.getBoundingClientRect().left - box.getBoundingClientRect().left + box.scrollLeft;
      const end = start + tab.offsetWidth;
      if (start < box.scrollLeft) box.scrollTo({ left: Math.max(0, start - 8) });
      else if (end > box.scrollLeft + box.clientWidth) box.scrollTo({ left: end - box.clientWidth + 8 });
    };
    ensureVisible();
    // Fonts and badges change the widths a moment after the first paint, so check once more.
    void document.fonts?.ready.then(ensureVisible);
    const later = window.setTimeout(ensureVisible, 500);
    return () => window.clearTimeout(later);
  }, [selected, row]);
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const target = nextTab(tabs.map(tab => tab.id), selected, event.key);
    if (!target) return;
    event.preventDefault();
    onSelect(target);
    refs.current.get(target)?.focus();
  };
  return (
    <div ref={row} className="tabs" data-more={more || undefined} role="tablist" aria-label={label} onKeyDown={onKeyDown}>
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
