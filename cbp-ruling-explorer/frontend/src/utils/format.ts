/** 年份格式化，缺失显示为破折号。 */
export function formatYear(year: number | null | undefined): string {
  return year != null && year > 0 ? String(year) : '—';
}

/** 日期格式化，缺失显示为破折号。 */
export function formatDate(value: string | null | undefined): string {
  return value ? value : '—';
}

/** 状态中文标签。 */
export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    active: '生效中',
    revoked: '已撤销',
    modified: '已修改',
    third_party: '第三方',
  };
  return map[status] ?? status;
}
