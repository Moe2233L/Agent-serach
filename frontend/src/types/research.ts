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
}
