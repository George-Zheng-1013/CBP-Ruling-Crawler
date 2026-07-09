import { describe, it, expect, beforeEach } from 'vitest';
import { useQueryStore } from './queryStore';

describe('queryStore URL sync', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/');
    useQueryStore.getState().reset();
    window.history.replaceState(null, '', '/');
  });

  it('toParams returns snake_case keys with correct defaults', () => {
    const p = useQueryStore.getState().toParams();
    expect(p).toEqual({
      keyword: '',
      ruling_no: '',
      year: undefined,
      status: '',
      hs_code: '',
      page: 1,
    });
  });

  it('setKeyword writes to URL and updates state (snake_case ruling_no)', () => {
    useQueryStore.getState().setKeyword('toy');
    expect(window.location.search).toContain('keyword=toy');
    expect(useQueryStore.getState().toParams().keyword).toBe('toy');
  });

  it('setYear writes a numeric year to URL', () => {
    useQueryStore.getState().setYear(2024);
    expect(window.location.search).toContain('year=2024');
    expect(useQueryStore.getState().toParams().year).toBe(2024);
  });

  it('setRulingNo writes ruling_no (snake_case) to URL', () => {
    useQueryStore.getState().setRulingNo('N12');
    expect(window.location.search).toContain('ruling_no=N12');
  });

  it('setPage does not reset page and writes page only when > 1', () => {
    useQueryStore.getState().setKeyword('x'); // 触发 page 重置为 1
    useQueryStore.getState().setPage(3);
    expect(window.location.search).toContain('page=3');
    expect(useQueryStore.getState().toParams().page).toBe(3);
  });

  it('changing a filter resets page to 1 and omits page param in URL', () => {
    useQueryStore.getState().setPage(5);
    useQueryStore.getState().setKeyword('new');
    expect(useQueryStore.getState().toParams().page).toBe(1);
    // syncUrl 仅在 page>1 时写 page 参数
    expect(window.location.search).not.toContain('page=');
  });
});
