export interface Bird {
  id: number;
  commonName: string;
  ukrainianName: string;
  scientificName: string;
  family: string;
  habitat: string;
  distribution: string;
  diet: string;
  averageSize: string;
  description: string;
  conservationStatus: string;
  sourceUrl: string;
  sources: string[];
}

export interface Prediction {
  speciesName: string;
  scientificName: string | null;
  confidence: number;
  rank: number;
}
export interface Analysis {
  id: number;
  analysisId: string;
  status: AnalysisState;
  analysisType: "image" | "audio";
  originalFileName: string;
  fileUrl: string;
  predictedSpecies: string;
  confidence: number;
  modelName: string;
  modelRevision: string;
  analysisDate: string;
  description: string;
  elapsedSeconds: number;
  bird: Bird | null;
  predictions: Prediction[];
  evaluation: {
    expectedLabel: string;
    expectedScientific: string;
    labelSource: string;
    top1Correct: boolean;
    top3Correct: boolean;
    experiment: string;
  } | null;
}
export type AnalysisState = "Pending" | "Queued" | "Processing" | "Completed" | "Failed";
export interface AcceptedAnalysis {
  analysisId: string;
  status: AnalysisState;
  statusUrl: string;
  historyId: number;
}
export interface AnalysisStatus {
  analysisId: string;
  historyId: number;
  analysisType: "image" | "audio";
  status: AnalysisState;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
  errorMessage: string | null;
  retryCount: number;
  correlationId: string;
  stalled: boolean;
  result: Analysis | null;
}
export interface AcceptedBatchItem {
  fileName: string;
  task: AcceptedAnalysis | null;
  error: string | null;
}
export const analysisStatusText: Record<AnalysisState, string> = {
  Pending: "Очікування в черзі",
  Queued: "Очікування в черзі",
  Processing: "Обробка",
  Completed: "Аналіз завершено",
  Failed: "Помилка аналізу",
};
export const isTerminal = (status: AnalysisState) => status === "Completed" || status === "Failed";
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}
export interface Summary {
  totalAnalyses: number;
  imageAnalyses: number;
  audioAnalyses: number;
  identifiedSpecies: number;
  averageConfidence: number | null;
  minConfidence: number | null;
  maxConfidence: number | null;
  labelledEvaluations: number;
}
export interface BatchItem {
  fileName: string;
  analysis: Analysis | null;
  error: string | null;
}
export interface SpeciesCount {
  species: string;
  count: number;
  averageConfidence: number;
}
export interface ConfidenceBin {
  label: string;
  count: number;
}
export interface BirdComparison {
  first: Bird;
  second: Bird;
}
export interface ModelComparison {
  first: Analysis;
  second: Analysis;
  conclusion: string;
}
export interface EvaluationStats {
  model: string;
  experiment: string;
  samples: number;
  top1Correct: number;
  top3Correct: number;
}

export const percent = (value: number | null | undefined) =>
  value == null ? "—" : `${(value * 100).toFixed(1)}%`;
export const birdName = (analysis: Analysis) =>
  analysis.bird?.ukrainianName ||
  analysis.bird?.commonName ||
  analysis.predictedSpecies;
export const birdFields: [keyof Bird, string][] = [
  ["scientificName", "Наукова назва"],
  ["family", "Родина"],
  ["habitat", "Середовище"],
  ["distribution", "Поширення"],
  ["diet", "Живлення"],
  ["averageSize", "Розміри"],
  ["conservationStatus", "Охоронний статус"],
  ["description", "Опис"],
];
