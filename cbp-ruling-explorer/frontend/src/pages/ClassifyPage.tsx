import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { classifyProduct, getRagIndexStatus } from '../api/classify';
import { saveReferencePdfs } from '../api/rulings';
import type {
  ClassificationResult,
  ProductClassificationInput,
  RagIndexStatus,
} from '../types/classification';

const EMPTY: ProductClassificationInput = {
  productName: '',
  productType: '',
  description: '',
  materials: [],
  components: [],
  functions: [],
  intendedUse: '',
  technicalSpecs: '',
  countryOfOrigin: '',
};

const confidenceLabel = { high: '高', medium: '中', low: '低' };

const PROGRESS_STAGES = [
  '整理商品特征与生成检索查询',
  '检索 CBP 裁定案例',
  '使用专用模型重排序',
  '校验现行 USITC HTS 税号',
  '生成中文归类结论与引用',
];
const rulingStatusLabel: Record<string, string> = {
  active: '有效',
  revoked: '已撤销',
  modified: '已修改',
};

function splitList(value: string): string[] {
  return value.split(/[,，;；\n]/).map((item) => item.trim()).filter(Boolean);
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="subheading block mb-1.5">
        {label}{required && <span className="text-red-600 ml-1">*</span>}
      </span>
      {children}
    </label>
  );
}

export function ClassifyPage() {
  const [form, setForm] = useState(EMPTY);
  const [listFields, setListFields] = useState({
    materials: '',
    components: '',
    functions: '',
  });
  const [index, setIndex] = useState<RagIndexStatus | null>(null);
  const [result, setResult] = useState<ClassificationResult | null>(null);
  const [resultProductName, setResultProductName] = useState('');
  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    getRagIndexStatus().then(setIndex).catch((err: Error) => setError(err.message));
  }, []);
  useEffect(() => {
    if (!loading) return;
    setProgressStep(0);
    const timer = window.setInterval(() => {
      setProgressStep((current) => Math.min(current + 1, PROGRESS_STAGES.length - 1));
    }, 2500);
    return () => window.clearInterval(timer);
  }, [loading]);

  const update = (key: keyof ProductClassificationInput, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const input = {
        ...form,
        materials: splitList(listFields.materials),
        components: splitList(listFields.components),
        functions: splitList(listFields.functions),
      };
      const classification = await classifyProduct(input);
      setResult(classification);
      setResultProductName(input.productName.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : '归类请求失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div>
        <h1 className="display">智能 HTSUS 归类</h1>
        <p className="body text-gray-600 mt-2">
          根据商品特征检索 CBP 裁定案例，并使用当前 USITC HTS 校验候选税号。
        </p>
      </div>

      {index && (
        <div className={`card p-4 body ${index.ready ? 'border-green-200' : 'border-amber-300'}`}>
          {index.ready
            ? `知识库已就绪：${index.rulings.toLocaleString()} 条裁定、${index.chunks.toLocaleString()} 个证据片段，${index.htsVersion}`
            : '知识库尚未建立。请先配置 backend/config.json，再运行 python -m app.rag sync。'}
        </div>
      )}

      <form onSubmit={submit} className="card p-5 sm:p-6 space-y-5">
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="产品名称" required>
            <input className="input w-full" value={form.productName}
              onChange={(e) => update('productName', e.target.value)} required />
          </Field>
          <Field label="产品类型">
            <input className="input w-full" value={form.productType}
              onChange={(e) => update('productType', e.target.value)}
              placeholder="例如：电子模块、纺织品、机械零件" />
          </Field>
        </div>

        <Field label="完整产品描述">
          <textarea className="input w-full min-h-32 resize-y" value={form.description}
            onChange={(e) => update('description', e.target.value)}
            placeholder="描述商品的结构、工作原理、进口时状态、功能和使用场景。" />
        </Field>

        <div className="grid sm:grid-cols-3 gap-4">
          {(['materials', 'components', 'functions'] as const).map((key) => (
            <Field key={key} label={{ materials: '材料', components: '主要部件', functions: '功能' }[key]}>
              <textarea className="input w-full min-h-20 resize-y" value={listFields[key]}
                onChange={(e) => setListFields((current) => ({ ...current, [key]: e.target.value }))}
                placeholder="用逗号或换行分隔" />
            </Field>
          ))}
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="主要用途">
            <textarea className="input w-full min-h-20 resize-y" value={form.intendedUse}
              onChange={(e) => update('intendedUse', e.target.value)} />
          </Field>
          <Field label="技术规格">
            <textarea className="input w-full min-h-20 resize-y" value={form.technicalSpecs}
              onChange={(e) => update('technicalSpecs', e.target.value)}
              placeholder="尺寸、功率、电压、容量、加工方式等" />
          </Field>
        </div>

        <Field label="原产国（可选）">
          <input className="input w-full sm:w-1/2" value={form.countryOfOrigin}
            onChange={(e) => update('countryOfOrigin', e.target.value)} />
        </Field>

        <button className="btn btn-primary min-w-32" disabled={loading || index?.ready === false}>
          {loading ? '正在检索与分析…' : '开始智能归类'}
        </button>
      </form>

      {error && <div className="card p-4 text-red-700 body">{error}</div>}
      {loading && <ClassificationProgress activeStep={progressStep} />}
      {result && <ResultView result={result} productName={resultProductName} />}
    </div>
  );
}

function ClassificationProgress({ activeStep }: { activeStep: number }) {
  const width = `${Math.min(92, 12 + activeStep * 20)}%`;

  return (
    <section className="card p-5 sm:p-6" aria-live="polite">
      <div className="flex items-center justify-between gap-3">
        <h2 className="heading">正在进行智能归类</h2>
        <span className="caption">阶段进度</span>
      </div>
      <div className="h-2 rounded-full bg-gray-100 overflow-hidden mt-4">
        <div
          className="h-full rounded-full bg-blue transition-all duration-700"
          style={{ width }}
        />
      </div>
      <ol className="mt-4 space-y-2">
        {PROGRESS_STAGES.map((stage, index) => {
          const active = index === activeStep;
          const complete = index < activeStep;
          return (
            <li
              key={stage}
              className={`body flex items-center gap-2 ${
                active ? 'text-blue font-medium' : complete ? 'text-green-700' : 'text-gray-400'
              }`}
            >
              <span aria-hidden="true">{complete ? '✓' : active ? '●' : '○'}</span>
              <span>{stage}</span>
              {active && <span className="caption">处理中</span>}
            </li>
          );
        })}
      </ol>
      <p className="caption mt-4">各阶段耗时取决于模型服务和检索规模，完成后会自动显示结果。</p>
    </section>
  );
}
function ResultView({ result, productName }: { result: ClassificationResult; productName: string }) {
  const [savingPdfs, setSavingPdfs] = useState(false);
  const [pdfMessage, setPdfMessage] = useState('');
  const [pdfError, setPdfError] = useState('');

  const downloadAllPdfs = async () => {
    setSavingPdfs(true);
    setPdfMessage('');
    setPdfError('');
    try {
      const saved = await saveReferencePdfs(
        productName,
        result.references.map((item) => item.rulingNo),
      );
      const failure = saved.failed.length > 0
        ? `；失败：${saved.failed.map((item) => item.rulingNo).join('、')}`
        : '';
      setPdfMessage(`已保存 ${saved.downloaded.length} 份 PDF：${saved.directory}${failure}`);
    } catch (err) {
      setPdfError(err instanceof Error ? err.message : '参考案例 PDF 保存失败');
    } finally {
      setSavingPdfs(false);
    }
  };

  return (
    <div className="space-y-5">
      {result.warnings.map((warning) => (
        <div key={warning} className="card p-4 bg-amber-50 text-amber-900 body">{warning}</div>
      ))}

      <section className="card p-5 sm:p-6">
        <h2 className="heading mb-4">归类结论</h2>
        {result.primary ? (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <span className="mono text-2xl font-bold text-navy">{result.primary.htsCode}</span>
              <span className="chip chip-accent">置信度：{confidenceLabel[result.primary.confidence]}</span>
              <span className="chip">{result.htsVersion}</span>
            </div>
            <p className="subheading mt-3">{result.primary.description}</p>
            {result.primary.parentPath && <p className="caption mt-1">{result.primary.parentPath}</p>}
            <ul className="list-disc pl-5 body mt-4 space-y-1">
              {result.primary.basis.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </>
        ) : (
          <p className="body">现有证据不足，暂不输出未经校验的10位税号。</p>
        )}
      </section>

      {result.alternatives.length > 0 && (
        <section className="card p-5">
          <h2 className="heading mb-3">备选税号</h2>
          <div className="space-y-3">
            {result.alternatives.map((item) => (
              <div key={item.htsCode}>
                <span className="mono font-semibold">{item.htsCode}</span>
                <span className="body ml-3">{item.description}</span>
                <p className="caption mt-1">{item.reason}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {result.missingInformation.length > 0 && (
        <section className="card p-5">
          <h2 className="heading mb-2">建议补充的信息</h2>
          <ul className="list-disc pl-5 body space-y-1">
            {result.missingInformation.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h2 className="heading">参考案例（{result.references.length}）</h2>
          {result.references.length > 0 && (
            <button
              type="button"
              className="btn btn-primary text-sm"
              onClick={downloadAllPdfs}
              disabled={savingPdfs}
            >
              {savingPdfs
                ? `正在保存 ${result.references.length} 份 PDF…`
                : '下载全部 PDF'}
            </button>
          )}
        </div>
        {pdfMessage && <p className="body text-green-700 break-all" aria-live="polite">{pdfMessage}</p>}
        {pdfError && <p className="body text-red-700" role="alert">{pdfError}</p>}
        {result.references.map((item) => (
          <details key={item.rulingNo} className="card p-4">
            <summary className="cursor-pointer list-none">
              <div className="flex flex-wrap gap-2 items-center">
                <Link className="mono font-bold text-blue hover:underline"
                  to={`/ruling/${item.rulingNo}`}>{item.rulingNo}</Link>
                <span className="chip">{rulingStatusLabel[item.status] ?? item.status}</span>
                {item.hsCodes.map((code) => <span className="chip chip-accent mono" key={code}>{code}</span>)}
              </div>
              <p className="subheading mt-2">{item.subject}</p>
            </summary>
            <div className="mt-4 space-y-3">
              {item.similarities.length > 0 && <p className="body"><b>相似点：</b>{item.similarities.join('；')}</p>}
              {item.differences.length > 0 && <p className="body"><b>差异点：</b>{item.differences.join('；')}</p>}
              <blockquote className="body whitespace-pre-wrap bg-gray-50 border-l-4 border-blue px-4 py-3">
                {item.excerpt}
              </blockquote>
              <a href={item.detailUrl} target="_blank" rel="noreferrer"
                className="text-sm text-blue hover:underline">打开 CBP 官方案例</a>
            </div>
          </details>
        ))}
      </section>

      <p className="caption border-t pt-4">{result.disclaimer}</p>
    </div>
  );
}
