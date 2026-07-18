import client from './client';
import type {
  ClassificationResult,
  ProductClassificationInput,
  RagIndexStatus,
} from '../types/classification';

function toSnakeCase(input: ProductClassificationInput) {
  return {
    product_name: input.productName,
    product_type: input.productType,
    description: input.description,
    materials: input.materials,
    components: input.components,
    functions: input.functions,
    intended_use: input.intendedUse,
    technical_specs: input.technicalSpecs,
    country_of_origin: input.countryOfOrigin,
  };
}

export async function classifyProduct(
  input: ProductClassificationInput,
): Promise<ClassificationResult> {
  const response = await client.post<ClassificationResult>(
    '/api/classify',
    toSnakeCase(input),
    { timeout: 180000 },
  );
  return response.data;
}

export async function getRagIndexStatus(): Promise<RagIndexStatus> {
  const response = await client.get<RagIndexStatus>('/api/classify/index-status');
  return response.data;
}
