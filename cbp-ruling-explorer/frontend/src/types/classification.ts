export interface ProductClassificationInput {
  productName: string;
  productType: string;
  description: string;
  materials: string[];
  components: string[];
  functions: string[];
  intendedUse: string;
  technicalSpecs: string;
  countryOfOrigin: string;
}

export interface ClassificationPrimary {
  htsCode: string;
  description: string;
  parentPath: string;
  confidence: 'high' | 'medium' | 'low';
  basis: string[];
}

export interface ClassificationAlternative {
  htsCode: string;
  description: string;
  reason: string;
}

export interface CaseReference {
  rulingNo: string;
  subject: string;
  rulingDate: string;
  year: number;
  hsCodes: string[];
  status: string;
  detailUrl: string;
  section: string;
  excerpt: string;
  similarities: string[];
  differences: string[];
}

export interface ClassificationResult {
  productProfile: string;
  primary: ClassificationPrimary | null;
  alternatives: ClassificationAlternative[];
  references: CaseReference[];
  missingInformation: string[];
  warnings: string[];
  htsVersion: string;
  disclaimer: string;
}

export interface RagIndexStatus {
  ready: boolean;
  chunks: number;
  rulings: number;
  htsEntries: number;
  htsVersion: string;
}
