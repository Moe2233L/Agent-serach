export interface SubtaskState {
  id: number
  title: string
  query: string
  status: string
  summary?: string
  iteration?: number
}

export interface LogState {
  phase: string
  phaseLabel: string
  message: string
}

export interface CriticFeedback {
  overall_score: number
  dimensions: Record<string, number>
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
}

export interface SubtaskCriticFeedback extends CriticFeedback {
  id: number
}

export interface ResearchCardData {
  id: string
  topic: string
  subtasks: SubtaskState[]
  logs: LogState[]
  report: string
  status: string
  error: string
  timestamp?: number
  controller?: AbortController | null
  subtaskCriticFeedback?: Record<number, CriticFeedback>
  reportCriticFeedback?: CriticFeedback | null
  reportRewriting?: boolean
}

export const REPORT_DIMENSIONS = ["structure", "depth", "citation_accuracy", "readability", "completeness"]
export const SUBTASK_DIMENSIONS = ["relevance", "depth", "clarity", "citation_quality"]

export function ensureCriticFeedback(fb: CriticFeedback | null | undefined, expectedDims: string[]): CriticFeedback | null {
  if (!fb) return null
  const dims: Record<string, number> = {}
  for (const key of expectedDims) {
    const val = fb.dimensions?.[key]
    dims[key] = typeof val === "number" && val >= 1 && val <= 10 ? Math.round(val) : 7
  }
  const scores = Object.values(dims)
  const overall = typeof fb.overall_score === "number" && fb.overall_score >= 1 && fb.overall_score <= 10
    ? Math.round(fb.overall_score) : Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
  return {
    overall_score: overall,
    dimensions: dims,
    strengths: Array.isArray(fb.strengths) ? fb.strengths : [],
    weaknesses: Array.isArray(fb.weaknesses) ? fb.weaknesses : [],
    suggestions: Array.isArray(fb.suggestions) ? fb.suggestions : [],
  }
}
