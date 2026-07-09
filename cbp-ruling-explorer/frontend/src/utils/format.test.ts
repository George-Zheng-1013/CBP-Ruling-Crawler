import { describe, it, expect } from 'vitest';
import { formatYear, formatDate, statusLabel } from './format';

describe('formatYear', () => {
  it('returns the year as string when valid', () => {
    expect(formatYear(2024)).toBe('2024');
  });
  it('returns em dash for 0 / null / undefined', () => {
    expect(formatYear(0)).toBe('—');
    expect(formatYear(null)).toBe('—');
    expect(formatYear(undefined)).toBe('—');
  });
});

describe('formatDate', () => {
  it('returns the value when present', () => {
    expect(formatDate('2023-05-12')).toBe('2023-05-12');
  });
  it('returns em dash for empty / null / undefined', () => {
    expect(formatDate('')).toBe('—');
    expect(formatDate(null)).toBe('—');
    expect(formatDate(undefined)).toBe('—');
  });
});

describe('statusLabel', () => {
  it('maps known statuses to Chinese labels', () => {
    expect(statusLabel('active')).toBe('生效中');
    expect(statusLabel('revoked')).toBe('已撤销');
    expect(statusLabel('modified')).toBe('已修改');
    expect(statusLabel('third_party')).toBe('第三方');
  });
  it('falls back to the raw status for unknown values', () => {
    expect(statusLabel('weird_status')).toBe('weird_status');
  });
});
