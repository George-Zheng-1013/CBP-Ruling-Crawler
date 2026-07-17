interface Props {
  message: string;
}

export function ParseFailedBadge({ message }: Props) {
  return (
    <div className="mt-3 p-3 rounded-md bg-red-50 border border-red-200 text-sm text-red-700">
      <strong>解析失败</strong>
      {message ? `：${message}` : '，该裁定内容解析时出错，部分字段可能缺失。'}
    </div>
  );
}
