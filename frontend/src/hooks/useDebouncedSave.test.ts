import { renderHook, act } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { useDebouncedSave } from './useDebouncedSave';

// Mock the saveAnswer function to control its behavior per test
vi.mock('../lib/questionnaire', () => ({
  saveAnswer: vi.fn(),
}));

import { saveAnswer } from '../lib/questionnaire';

/**
 * useDebouncedSave fake-timer tests using vi.useFakeTimers().
 *
 * The debounce (1.5s) and retry backoff ([1s, 2s, 4s]) are simulated
 * via timer advancement, not real waits. Critical: fake timers do NOT
 * automatically flush pending microtasks (Promise chains from mocked
 * saveAnswer), so every timer advance is wrapped in `act()` with an
 * explicit `await Promise.resolve()` to flush the microtask queue
 * before asserting state — this is RESEARCH Pitfall 4.
 */
describe('useDebouncedSave', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('debounces by 1500ms before calling saveAnswer', async () => {
    const onStateChange = vi.fn();
    const { result } = renderHook(() => useDebouncedSave(1, onStateChange));

    // Schedule a save
    result.current.schedule('q-1', 'cat-1', 2);

    // Before the debounce window, saveAnswer should not be called
    await act(async () => {
      vi.advanceTimersByTime(500);
      await Promise.resolve();
    });
    expect(vi.mocked(saveAnswer)).not.toHaveBeenCalled();

    // After the full 1500ms, saveAnswer should be called exactly once
    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });

    expect(vi.mocked(saveAnswer)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(saveAnswer)).toHaveBeenCalledWith(1, 'q-1', {
      question_id: 'q-1',
      category_id: 'cat-1',
      score: 2,
    });

    // Verify state progression: idle -> saving -> saved
    expect(onStateChange.mock.calls).toContainEqual(['q-1', 'saving']);
    expect(onStateChange.mock.calls).toContainEqual(['q-1', 'saved']);
  });

  it('resets debounce timer and uses last value (last-write-wins)', async () => {
    const onStateChange = vi.fn();
    const { result } = renderHook(() => useDebouncedSave(1, onStateChange));

    // Schedule first value
    result.current.schedule('q-1', 'cat-1', 2);

    // Advance partway through debounce
    await act(async () => {
      vi.advanceTimersByTime(500);
      await Promise.resolve();
    });

    // Schedule again with different value — this resets the debounce timer
    result.current.schedule('q-1', 'cat-1', 4);

    // Advance another 500ms (still under 1500ms from the second schedule)
    await act(async () => {
      vi.advanceTimersByTime(500);
      await Promise.resolve();
    });

    // saveAnswer should still not have been called
    expect(vi.mocked(saveAnswer)).not.toHaveBeenCalled();

    // Advance the remaining 1000ms from the second schedule
    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });

    // saveAnswer called exactly once with the SECOND value (score: 4)
    expect(vi.mocked(saveAnswer)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(saveAnswer)).toHaveBeenCalledWith(1, 'q-1', {
      question_id: 'q-1',
      category_id: 'cat-1',
      score: 4, // The second, later value
    });
  });

  it('retries on failure and eventually succeeds', async () => {
    const onStateChange = vi.fn();
    const { result } = renderHook(() => useDebouncedSave(1, onStateChange));

    // Mock saveAnswer to fail twice, then succeed
    vi.mocked(saveAnswer)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockRejectedValueOnce(new Error('Network error'))
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .mockResolvedValueOnce({ question_id: 'q-1' } as any);

    result.current.schedule('q-1', 'cat-1', 2);

    // Advance past debounce window (1500ms)
    await act(async () => {
      vi.advanceTimersByTime(1500);
      await Promise.resolve();
    });

    // First attempt made and failed, now awaiting first backoff (1000ms)
    expect(vi.mocked(saveAnswer)).toHaveBeenCalledTimes(1);
    expect(onStateChange.mock.calls).toContainEqual(['q-1', 'saving']);

    // Advance through first retry backoff (1000ms) — triggers second attempt
    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });

    expect(vi.mocked(saveAnswer)).toHaveBeenCalledTimes(2);
    // "retrying" state is set when attempt > 0 (the second attempt)
    expect(onStateChange.mock.calls).toContainEqual(['q-1', 'retrying']);

    // Advance through second retry backoff (2000ms) — triggers third attempt
    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    // Now should have succeeded on the third attempt
    expect(vi.mocked(saveAnswer)).toHaveBeenCalledTimes(3);
    expect(onStateChange.mock.calls).toContainEqual(['q-1', 'saved']);
  });

  it('enters terminal failed state after exhausting all retries', async () => {
    const onStateChange = vi.fn();
    const { result } = renderHook(() => useDebouncedSave(1, onStateChange));

    // Mock saveAnswer to always reject (need 4 rejections for 1 initial + 3 retries)
    vi.mocked(saveAnswer)
      .mockRejectedValueOnce(new Error('Persistent error'))
      .mockRejectedValueOnce(new Error('Persistent error'))
      .mockRejectedValueOnce(new Error('Persistent error'))
      .mockRejectedValueOnce(new Error('Persistent error'));

    result.current.schedule('q-1', 'cat-1', 2);

    // Advance past debounce window (1500ms) — first attempt
    await act(async () => {
      vi.advanceTimersByTime(1500);
      await Promise.resolve();
    });

    expect(vi.mocked(saveAnswer)).toHaveBeenCalledTimes(1);

    // Advance through first retry backoff (1000ms) — second attempt
    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });

    expect(vi.mocked(saveAnswer)).toHaveBeenCalledTimes(2);

    // Advance through second retry backoff (2000ms) — third attempt
    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(vi.mocked(saveAnswer)).toHaveBeenCalledTimes(3);

    // Advance through third retry backoff (4000ms) — fourth and final attempt
    await act(async () => {
      vi.advanceTimersByTime(4000);
      await Promise.resolve();
    });

    // Fourth attempt (last retry), then terminal failed state
    expect(vi.mocked(saveAnswer)).toHaveBeenCalledTimes(4);
    expect(onStateChange.mock.calls).toContainEqual(['q-1', 'failed']);
  });

  it('treats HTTP 429 as non-escalating rate-limit (no retry consumed)', async () => {
    const onStateChange = vi.fn();
    const { result } = renderHook(() => useDebouncedSave(1, onStateChange));

    // Mock saveAnswer to reject with 429
    const error429 = new Error('Too many requests');
    Object.defineProperty(error429, 'response', {
      value: { status: 429 },
      enumerable: false,
    });
    vi.mocked(saveAnswer).mockRejectedValue(error429);

    result.current.schedule('q-1', 'cat-1', 2);

    // Advance past debounce window only
    await act(async () => {
      vi.advanceTimersByTime(1500);
      await Promise.resolve();
    });

    // saveAnswer called exactly ONCE (429 returns immediately, no retry)
    expect(vi.mocked(saveAnswer)).toHaveBeenCalledTimes(1);

    // State should show rate-limited, no retrying state
    expect(onStateChange.mock.calls).toContainEqual(['q-1', 'saving']);
    expect(onStateChange.mock.calls).toContainEqual(['q-1', 'rate-limited']);

    // Verify retrying state was NOT called
    const retryingCalls = onStateChange.mock.calls.filter(([, state]) => state === 'retrying');
    expect(retryingCalls).toHaveLength(0);
  });
});
