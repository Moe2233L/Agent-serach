export interface SubtaskPlan {
  id: number
  title: string
  query: string
}

export interface Progress {
  current: number
  total: number
}

export interface SubtaskStatusPayload {
  id: number
  status: string
  title: string
  progress?: Progress
}

export interface SubtaskCompletedPayload {
  id: number
  title: string
  summary: string
}

export interface LogPayload {
  phase: string
  message: string
}

export interface ReportPayload {
  report: string
}

export interface SubtasksPayload {
  subtasks: SubtaskPlan[]
}

export interface SSEEvent {
  event: string
  data: any
}
