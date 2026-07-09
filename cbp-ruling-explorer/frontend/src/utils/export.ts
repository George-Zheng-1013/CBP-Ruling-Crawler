import { RulingItemFE } from '../types/ruling';

/** 触发浏览器下载（Blob 方式）。 */
export function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** 前端兜底导出：基于当前已加载列表项生成 CSV（UTF-8 BOM）。 */
export function downloadCsvFromItems(
  items: RulingItemFE[],
  filename = 'cbp_rulings.csv',
): void {
  const headers = [
    'ruling_no',
    'subject',
    'year',
    'hs_code',
    'status',
    'parse_failed',
  ];
  const escape = (v: unknown) => {
    const s = String(v ?? '');
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [headers.join(',')];
  for (const it of items) {
    lines.push(
      [it.rulingNo, it.subject, it.year, it.hsCode, it.status, it.parseFailed ? 1 : 0]
        .map(escape)
        .join(','),
    );
  }
  // \ufeff BOM 保证 Excel 正确识别 UTF-8 中文。
  const blob = new Blob(['\ufeff' + lines.join('\n')], {
    type: 'text/csv;charset=utf-8',
  });
  triggerDownload(blob, filename);
}
