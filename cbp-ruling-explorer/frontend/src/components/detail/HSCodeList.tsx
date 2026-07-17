import { getChapterNum } from '../../utils/htsChapters';

interface Props {
  mainHsCode: string;
  hsCodes: string[];
}

export function HSCodeList({ mainHsCode, hsCodes }: Props) {
  const all = mainHsCode
    ? [mainHsCode, ...hsCodes.filter((c) => c !== mainHsCode)]
    : hsCodes;
  const unique = Array.from(new Set(all.filter(Boolean)));

  return (
    <div className="mt-3">
      <p className="caption mb-1.5">HS Code</p>
      <div className="flex flex-wrap gap-1.5">
        {unique.length === 0 ? (
          <span className="caption">—</span>
        ) : (
          unique.map((c) => {
            const ch = getChapterNum(c);
            const label = ch ? `${c} · CH${ch}` : c;
            return (
              <span key={c} className="chip text-xs font-mono">
                {label}
              </span>
            );
          })
        )}
      </div>
    </div>
  );
}
