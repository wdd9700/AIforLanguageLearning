export interface EssayScore {
  vocabulary: number;
  grammar: number;
  fluency: number;
  logic: number;
  content: number;
  structure: number;
  total: number;
}

export interface EssayCorrectionResult {
  original: string;
  correction: string;
  scores: EssayScore;
  feedback: string;
  suggestions?: string[];
  questions?: string[];
  improvements?: string[];
  evaluation?: string;
}
