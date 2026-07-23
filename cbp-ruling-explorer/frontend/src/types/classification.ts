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

export type ClassificationNodeStatus = 'selected' | 'excluded' | 'pending';

export interface ClassificationEvidence {
  id: string;
  type: 'product_input' | 'hts_legal' | 'hts_entry' | 'cbp_case' | 'cbp_guide';
  title: string;
  excerpt: string;
  url: string;
  page: number | null;
  rulingNo: string;
  htsCode: string;
  status: string;
}

export interface ClassificationTreeNode {
  id: string;
  nodeType: 'product_facts' | 'interpretation_rule' | 'legal_note'
    | 'candidate_heading' | 'subheading' | 'case';
  status: ClassificationNodeStatus;
  title: string;
  htsCode: string;
  rationale: string[];
  missingInformation: string[];
  evidenceIds: string[];
  children: ClassificationTreeNode[];
}

export interface ClassificationTree {
  root: ClassificationTreeNode;
  evidence: ClassificationEvidence[];
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
  classificationTree: ClassificationTree | null;
}

export interface RagIndexStatus {
  ready: boolean;
  chunks: number;
  rulings: number;
  htsEntries: number;
  htsVersion: string;
  legalChunks: number;
}
