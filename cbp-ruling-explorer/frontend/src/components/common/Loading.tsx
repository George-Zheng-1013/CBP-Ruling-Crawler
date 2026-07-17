interface Props {
  label?: string;
}

export function Loading({ label = '加载中…' }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <div className="spinner" />
      <span className="caption">{label}</span>
    </div>
  );
}
