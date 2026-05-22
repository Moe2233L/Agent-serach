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
