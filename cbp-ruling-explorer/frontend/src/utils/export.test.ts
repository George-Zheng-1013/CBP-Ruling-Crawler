import { describe, it, expect, beforeEach, vi } from 'vitest';
import { downloadCsvFromItems } from './export';
import type { RulingItemFE } from '../types/ruling';

/** 读取 jsdom Blob 的原始字节（不剥 BOM）。 */
function blobBytes(blob: Blob): Promise<Uint8Array> {
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(new Uint8Array(fr.result as ArrayBuffer));
    fr.onerror = () => reject(fr.error);
    fr.readAsArrayBuffer(blob);
  });
}

/** 将 Blob 以 UTF-8 解码为文本（TextDecoder 默认会剥除前导 BOM）。 */
function blobText(blob: Blob): Promise<string> {
  return blobBytes(blob).then((b) => new TextDecoder('utf-8').decode(b));
}

describe('downloadCsvFromItems', () => {
  beforeEach(() => {
    // 拦截 URL.createObjectURL 以捕获生成的 Blob；屏蔽锚点 click 的导航警告
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:test'),
      revokeObjectURL: vi.fn(),
    });
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  });

  it('produces a UTF-8 BOM CSV with correct header and data rows', async () => {
    const items: RulingItemFE[] = [
      { rulingNo: 'N12345', subject: 'Toy', year: 2023, hsCode: '9503', hsCodes: ['9503'], status: 'active', parseFailed: false },
      { rulingNo: 'N33333', subject: 'Failed', year: 2022, hsCode: '8518', hsCodes: ['8518'], status: 'active', parseFailed: true },
    ];
    downloadCsvFromItems(items, 'out.csv');

    const blob = (globalThis as any).URL.createObjectURL.mock.calls[0][0];
    const bytes = await blobBytes(blob);

    // 前 3 字节应为 UTF-8 BOM (EF BB BF)
    expect(Array.from(bytes.subarray(0, 3))).toEqual([0xef, 0xbb, 0xbf]);

    const lines = (await blobText(blob)).split('\n');
    expect(lines[0]).toBe('ruling_no,subject,year,hs_code,status,parse_failed');
    expect(lines[1]).toBe('N12345,Toy,2023,9503,active,0');
    expect(lines[2]).toBe('N33333,Failed,2022,8518,active,1');
  });

  it('escapes commas and quotes per RFC 4180', async () => {
    const items: RulingItemFE[] = [
      { rulingNo: 'X1', subject: 'a,b "c"', year: 2024, hsCode: '1', hsCodes: ['1'], status: 'active', parseFailed: false },
    ];
    downloadCsvFromItems(items);
    const blob = (globalThis as any).URL.createObjectURL.mock.calls[0][0];
    const line = (await blobText(blob)).split('\n')[1];
    expect(line).toBe('X1,"a,b ""c""",2024,1,active,0');
  });
});
