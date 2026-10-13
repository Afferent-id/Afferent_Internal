/** Where a list, table or chart is in its life: first load, failed with nothing to show, or ready (which may still be empty). */
export interface LoadState { status: 'loading' | 'error' | 'ready'; retry?: () => void }

/**
 * Loading only counts before the first answer. An error only replaces the content when there is nothing older to show,
 * so a failed refresh never wipes a table that is already on screen.
 */
export function loadState(isLoading: boolean, error: unknown, hasData: boolean, retry?: () => void): LoadState {
  if (hasData) return { status: 'ready', retry };
  if (error) return { status: 'error', retry };
  return { status: isLoading ? 'loading' : 'ready', retry };
}
