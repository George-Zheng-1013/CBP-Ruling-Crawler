import axios, { AxiosError, AxiosInstance } from 'axios';

// 后端基地址：优先取 .env 中的 VITE_API_BASE，否则回落到本地默认。
const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:9000';

export interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T | null;
}

const client: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

/** 将 snake_case 键转换为 camelCase。 */
function toCamelCase(key: string): string {
  return key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

/** 递归地把对象/数组的键由 snake_case 转为 camelCase。 */
function deepToCamel(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(deepToCamel);
  }
  if (value !== null && typeof value === 'object') {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[toCamelCase(k)] = deepToCamel(v);
    }
    return out;
  }
  return value;
}

// 响应拦截器：解包 envelope，非 0 业务码或网络错误一律 reject。
client.interceptors.response.use(
  (response) => {
    const body = response.data as ApiEnvelope<unknown>;
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 0) {
        return Promise.reject(new Error(body.message || 'request failed'));
      }
      response.data = deepToCamel(body.data);
    }
    return response;
  },
  (error: AxiosError<ApiEnvelope<unknown>>) => {
    const message =
      error.response?.data?.message || error.message || 'network error';
    return Promise.reject(new Error(message));
  },
);

export { client, API_BASE };
export default client;
