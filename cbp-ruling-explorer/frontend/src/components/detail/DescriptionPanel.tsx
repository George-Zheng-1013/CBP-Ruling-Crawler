interface Props {
  text: string;
}

export function DescriptionPanel({ text }: Props) {
  return (
    <div className="card p-3 mt-3 max-h-[420px] overflow-auto">
      <p className="caption mb-1.5">全文描述</p>
      <div className="body whitespace-pre-wrap leading-relaxed">
        {text || '（无内容）'}
      </div>
    </div>
  );
}
