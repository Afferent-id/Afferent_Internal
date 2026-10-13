'use client';

import { useEffect, useRef, useState, type RefObject } from 'react';

/**
 * Tells which sides of a sideways-scrolling box still have more to show ("left", "right", "left right" or "").
 * Empty while the content fits, so a box that fits looks exactly as before. `watch` re-measures when it changes.
 */
export function useScrollCue(watch: unknown): [RefObject<HTMLDivElement | null>, string] {
  const ref = useRef<HTMLDivElement>(null);
  const [more, setMore] = useState('');
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const update = () => {
      const left = node.scrollLeft > 1;
      const right = node.scrollLeft + node.clientWidth < node.scrollWidth - 1;
      setMore(`${left ? 'left ' : ''}${right ? 'right' : ''}`.trim());
    };
    const frame = window.requestAnimationFrame(update);
    node.addEventListener('scroll', update, { passive: true });
    const observer = new ResizeObserver(update);
    observer.observe(node);
    const table = node.firstElementChild;
    if (table) observer.observe(table);
    return () => { window.cancelAnimationFrame(frame); node.removeEventListener('scroll', update); observer.disconnect(); };
  }, [watch]);
  return [ref, more];
}
