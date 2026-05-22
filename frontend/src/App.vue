<template>
  <ParticleNetwork />

  <div class="app-layout">
    <div class="layout-track" :class="{ shifted: layoutShifted }">
      <div class="left-panel">
        <div class="hero">
          <div class="hero-tagline">AI-Powered Research</div>
          <h1 class="hero-title">
            <span class="title-line">深度研究</span>
            <span class="title-line accent">智能洞察</span>
          </h1>
          <p class="hero-subtitle">让 AI 为你规划、搜索、总结，生成专业研究报告</p>

          <form class="input-group" @submit.prevent="handleSubmit">
            <div class="input-wrapper">
              <svg class="input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
              <input
                v-model="topic"
                type="text"
                class="input-field"
                placeholder="输入研究主题，例如：量子计算最新进展"
                :disabled="loading"
                @keydown.esc="topic = ''"
              />
            </div>
            <button type="submit" class="submit-btn" :disabled="loading || !topic.trim()">
              <span v-if="!loading">开始研究</span>
              <span v-else class="btn-loading"><span class="btn-spinner"></span>研究中...</span>
            </button>
          </form>

          <div class="params-row">
            <div class="param-group">
              <label class="param-label">搜索条数 <span class="param-val">{{ maxResults }}</span></label>
              <input type="range" v-model.number="maxResults" min="2" max="15" class="param-slider" :disabled="loading" />
            </div>
            <div class="param-group">
              <label class="param-label">子任务数 <span class="param-val">{{ subtaskCount }}</span></label>
              <input type="range" v-model.number="subtaskCount" min="1" max="6" class="param-slider" :disabled="loading" />
            </div>
          </div>

          <div class="params-row">
            <label class="deep-toggle">
              <input type="checkbox" v-model="deepMode" :disabled="loading" />
              <span class="deep-toggle-track">
                <span class="deep-toggle-thumb"></span>
              </span>
              <span class="deep-toggle-label">深度研究 <span class="deep-toggle-badge">迭代搜索</span></span>
            </label>
          </div>

          <div class="examples">
            <span class="examples-label">试试：</span>
            <button v-for="ex in examples" :key="ex" class="example-chip" :disabled="loading" @click="topic = ex">{{ ex }}</button>
          </div>

          <Transition name="history-slide">
            <div v-if="history.length > 0" class="history-section">
              <div class="history-header">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                <span>历史记录</span>
                <button class="history-clear" @click="clearHistory">清除</button>
              </div>
              <div class="history-list">
                <button v-for="item in history" :key="item.id" class="history-item" @click="openHistory(item)">
                  <span class="history-item-title">{{ item.topic }}</span>
                  <span class="history-item-time">{{ formatTime(item.timestamp) }}</span>
                </button>
              </div>
            </div>
          </Transition>

          <div class="hero-footer">
            <div class="footer-dot"></div>
            <span>后端已连接</span>
          </div>
        </div>
      </div>

      <Transition name="panel">
        <div class="right-panel" v-if="hasContent">
          <div class="panel-header">
            <span class="panel-title">
              {{ historyPreview ? '历史记录' : '研究任务' }}
              <span class="panel-count">{{ cards.length }}</span>
            </span>
            <button v-if="historyPreview" class="back-btn" @click="closeHistoryPreview">← 返回</button>
          </div>
          <div class="panel-body">
            <ResearchCard
              v-for="(card, i) in displayCards"
              :key="card.id"
              :topic="card.topic"
              :subtasks="card.subtasks"
              :logs="card.logs"
              :report="card.report"
              :status="card.status"
              :error="card.error"
              :is-history="!!historyPreview"
              :subtask-critic-feedback="card.subtaskCriticFeedback"
              :report-critic-feedback="card.reportCriticFeedback"
              :report-rewriting="card.reportRewriting"
              @remove="removeCard(i)"
              @cancel="handleCancel(i)"
            />
            <div v-if="historyPreview" class="history-followup">
              <div class="followup-heading">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                <span>追问</span>
              </div>
              <form class="followup-form" @submit.prevent="handleHistoryFollowup">
                <input
                  v-model="followupQuestion"
                  type="text"
                  class="followup-input"
                  placeholder="对此研究报告进行追问..."
                  :disabled="followupLoading"
                />
                <button type="submit" class="followup-send" :disabled="followupLoading || !followupQuestion.trim()">
                  <span v-if="followupLoading" class="followup-spinner"></span>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                </button>
              </form>
              <span v-if="followupError" class="followup-error">{{ followupError }}</span>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import ParticleNetwork from './components/ParticleNetwork.vue'
import ResearchCard from './components/ResearchCard.vue'
import type { ResearchCardData, SubtaskState, LogState } from './types/research'
import { readSSEStream } from './utils/sse'
import { ensureCriticFeedback, REPORT_DIMENSIONS, SUBTASK_DIMENSIONS } from './types/research'

const STORAGE_KEY = 'research_history'
const topic = ref('')
const loading = ref(false)
const maxResults = ref(5)
const subtaskCount = ref(3)
const deepMode = ref(false)
const cards = ref<ResearchCardData[]>([])
const history = ref<ResearchCardData[]>([])
const historyPreview = ref<ResearchCardData | null>(null)
const followupQuestion = ref('')
const followupLoading = ref(false)
const followupError = ref('')

const examples = [
  '人工智能在医疗领域的应用',
  '碳中和与新能源技术趋势',
  'Web3 与去中心化互联网',
]

const hasContent = computed(() => cards.value.length > 0 || !!historyPreview.value)

const displayCards = computed(() => {
  if (historyPreview.value) return [historyPreview.value]
  return cards.value
})

const layoutShifted = ref(false)

onMounted(() => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed: ResearchCardData[] = JSON.parse(raw)
      for (const record of parsed) {
        record.reportCriticFeedback = ensureCriticFeedback(record.reportCriticFeedback, REPORT_DIMENSIONS)
        if (record.subtaskCriticFeedback) {
          for (const id of Object.keys(record.subtaskCriticFeedback)) {
            record.subtaskCriticFeedback[+id] = ensureCriticFeedback(
              record.subtaskCriticFeedback[+id], SUBTASK_DIMENSIONS
            )!
          }
        }
      }
      history.value = parsed
    }
  } catch { history.value = [] }
})

function saveHistory() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history.value))
}

function formatTime(ts: number | undefined) {
  if (!ts) return ''
  const d = new Date(ts)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function openHistory(record: ResearchCardData) {
  historyPreview.value = record
  if (!layoutShifted.value) {
    layoutShifted.value = true
  } else {
    layoutShifted.value = false
    nextTick(() => {
      layoutShifted.value = true
    })
  }
}

function closeHistoryPreview() {
  historyPreview.value = null
  if (cards.value.length === 0) {
    layoutShifted.value = false
  }
}

function clearHistory() {
  history.value = []
  localStorage.removeItem(STORAGE_KEY)
  historyPreview.value = null
  if (cards.value.length === 0) {
    layoutShifted.value = false
  }
}

function removeCard(index: number) {
  cards.value.splice(index, 1)
  if (cards.value.length === 0 && !historyPreview.value) {
    layoutShifted.value = false
  }
}

function handleCancel(index: number) {
  const card = cards.value[index]
  if (card) {
    card.controller?.abort()
    removeCard(index)
  }
}

async function handleHistoryFollowup() {
  const q = followupQuestion.value.trim()
  const card = historyPreview.value
  if (!q || !card) return

  followupLoading.value = true
  followupError.value = ''

  try {
    const response = await fetch(`/research/${card.id}/followup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q }),
    })

    if (!response.ok) {
      followupError.value = `追问请求失败: ${response.status}`
      return
    }

    const reader = response.body?.getReader()
    if (!reader) { followupError.value = '无法读取响应流'; return }

    card.status = 'executing'

    await readSSEStream(reader, (event, data) => {
      if (event === 'report_append_prefix') {
        card.report = (card.report || '') + data.prefix
      } else if (event === 'report_chunk') {
        card.report = (card.report || '') + data.chunk
      } else if (event === 'followup_completed') {
        card.status = 'completed'
      }
    })
    card.status = 'completed'
  } catch (err: any) {
    if (err.name !== 'AbortError') followupError.value = err.message || '追问连接出错'
  } finally {
    followupLoading.value = false
    followupQuestion.value = ''
  }
}

async function handleSubmit() {
  const trimmed = topic.value.trim()
  if (!trimmed || loading.value) return

  loading.value = true
  const cardId = crypto.randomUUID()

  const card = reactive({
    id: cardId,
    topic: trimmed,
    subtasks: [] as SubtaskState[],
    logs: [] as LogState[],
    report: '',
    status: 'planning',
    error: '',
    controller: null as AbortController | null,
  }) as ResearchCardData
  cards.value.unshift(card)
  layoutShifted.value = true
  topic.value = ''

  try {
    const res = await fetch('/health')
    if (!res.ok) throw new Error('后端不可用')
  } catch {
    card.error = '后端服务未连接'
    return
  } finally {
    loading.value = false
  }

  startStream(card)
}

async function startStream(card: ResearchCardData) {
  const controller = new AbortController()
  card.controller = controller

  try {
    const response = await fetch('/research/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: card.topic,
        max_results: maxResults.value,
        subtask_count: subtaskCount.value,
        deep_mode: deepMode.value,
      }),
      signal: controller.signal,
    })

    if (!response.ok) {
      card.error = `请求失败: ${response.status}`
      return
    }

    const reader = response.body?.getReader()
    if (!reader) { card.error = '无法读取响应流'; return }

    await readSSEStream(reader, (event, data) => {
      handleCardEvent(card, event, data)
    }, controller.signal)
  } catch (err: any) {
    if (err.name !== 'AbortError') card.error = err.message || '连接出错'
  }
}

function handleCardEvent(card: ResearchCardData, event: string, data: any) {
  const phaseLabels: Record<string, string> = { planning: '规划', executing: '执行', reporting: '报告' }

  switch (event) {
    case 'log':
      card.logs.push({
        phase: data.phase,
        phaseLabel: phaseLabels[data.phase] || data.phase,
        message: data.message,
      })
      break

    case 'phase':
      card.status = data.phase
      break

    case 'subtasks':
      card.subtasks = data.subtasks.map((s: any) => ({ ...s, status: 'pending' }))
      break

    case 'subtask_status':
      updateSubtaskState(card, data.id, { status: data.status, iteration: data.iteration })
      if (card.status === 'planning') card.status = 'searching'
      break

    case 'subtask_completed':
      updateSubtaskState(card, data.id, { status: 'completed', summary: data.summary })
      break

    case 'subtask_critic':
      if (!card.subtaskCriticFeedback) card.subtaskCriticFeedback = {}
      card.subtaskCriticFeedback[data.id] = {
        overall_score: data.overall_score,
        dimensions: data.dimensions,
        strengths: data.strengths,
        weaknesses: data.weaknesses,
        suggestions: data.suggestions,
      }
      break

    case 'report':
      card.report = data.report
      break

    case 'report_chunk':
      card.report = (card.report || '') + data.chunk
      break

    case 'report_critic':
      card.reportCriticFeedback = {
        overall_score: data.overall_score,
        dimensions: data.dimensions,
        strengths: data.strengths,
        weaknesses: data.weaknesses,
        suggestions: data.suggestions,
      }
      break

    case 'report_rewriting':
      card.reportRewriting = true
      break

    case 'completed':
      card.status = 'completed'
      card.controller = null
      card.id = data.research_id
      const record: ResearchCardData = JSON.parse(JSON.stringify(card))
      record.reportCriticFeedback = ensureCriticFeedback(record.reportCriticFeedback, REPORT_DIMENSIONS)
      if (record.subtaskCriticFeedback) {
        for (const id of Object.keys(record.subtaskCriticFeedback)) {
          record.subtaskCriticFeedback[+id] = ensureCriticFeedback(
            record.subtaskCriticFeedback[+id], SUBTASK_DIMENSIONS
          )!
        }
      }
      record.logs = []
      record.subtasks = card.subtasks.map(s => ({ id: s.id, title: s.title, query: s.query, status: 'completed' as const, summary: s.summary || '' }))
      record.timestamp = Date.now()
      history.value.unshift(record)
      if (history.value.length > 50) history.value = history.value.slice(0, 50)
      saveHistory()
      break

    case 'error':
      card.error = data.error
      card.controller = null
      break
  }
}

function updateSubtaskState(card: ResearchCardData, id: number, updates: Partial<SubtaskState>) {
  const idx = card.subtasks.findIndex(s => s.id === id)
  if (idx !== -1) card.subtasks[idx] = { ...card.subtasks[idx], ...updates }
}
</script>

<style scoped>
.app-layout {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.layout-track {
  display: flex;
  align-items: stretch;
  width: 100%;
  max-width: 1400px;
  height: 100%;
  gap: 0;
  transition: transform 600ms cubic-bezier(0.4, 0, 0.2, 1),
              gap 600ms cubic-bezier(0.4, 0, 0.2, 1);
  transform: translateX(calc((100% - 600px) / 2));
}

.layout-track.shifted {
  transform: translateX(0);
  gap: 48px;
}

.layout-track.shifted .left-panel {
  width: calc(50% - 24px);
  flex-shrink: 1;
}

.layout-track.shifted .right-panel {
  flex: 1;
  min-width: 0;
}

.left-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 24px;
  width: 600px;
  flex-shrink: 0;
  transition: width 600ms cubic-bezier(0.4, 0, 0.2, 1);
}

.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 20px;
  width: 100%;
}

.hero-tagline {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--accent-blue);
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(8px);
  padding: 7px 18px;
  border-radius: 20px;
  border: 1px solid rgba(59, 130, 246, 0.15);
}

.hero-title { display: flex; flex-direction: column; gap: 3px; }
.title-line { display: block; font-size: 46px; font-weight: 700; line-height: 1.15; color: var(--text-primary); letter-spacing: -0.5px; }
.title-line.accent {
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-indigo), var(--accent-cyan));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.hero-subtitle { font-size: 15px; color: var(--text-secondary); line-height: 1.6; max-width: 480px; }

.input-group { display: flex; gap: 10px; width: 100%; }
.input-wrapper { flex: 1; position: relative; }
.input-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: var(--text-muted); pointer-events: none; }
.input-field {
  width: 100%; height: 48px; padding: 0 14px 0 42px;
  background: rgba(255,255,255,0.04); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.08); border-radius: var(--radius-md);
  color: var(--text-primary); font-size: 14px; font-family: 'Exo', sans-serif;
  outline: none; transition: all var(--transition-smooth); box-shadow: var(--glass-highlight);
}
.input-field:focus { border-color: rgba(59,130,246,0.35); background: rgba(255,255,255,0.07); box-shadow: var(--glass-highlight), 0 0 0 3px rgba(59,130,246,0.06); }
.input-field::placeholder { color: var(--text-muted); }
.input-field:disabled { opacity: 0.5; }

.submit-btn {
  height: 48px; padding: 0 24px;
  background: rgba(59,130,246,0.08); backdrop-filter: blur(12px);
  border: 1px solid rgba(59,130,246,0.18); border-radius: var(--radius-md);
  color: var(--accent-blue); font-size: 14px; font-weight: 600; font-family: 'Exo', sans-serif;
  cursor: pointer; transition: all var(--transition-smooth); white-space: nowrap; flex-shrink: 0; box-shadow: var(--glass-highlight);
}
.submit-btn:hover:not(:disabled) { background: rgba(59,130,246,0.14); border-color: rgba(59,130,246,0.30); box-shadow: var(--glass-highlight), 0 8px 24px rgba(59,130,246,0.15); transform: translateY(-1px); color: #fff; }
.submit-btn:active:not(:disabled) { transform: scale(0.97); background: rgba(59,130,246,0.18); box-shadow: var(--glass-highlight), 0 4px 12px rgba(59,130,246,0.10); }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-loading { display: flex; align-items: center; gap: 6px; }
.btn-spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.params-row { display: flex; gap: 16px; width: 100%; }
.param-group { flex: 1; }
.param-label { display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: var(--text-muted); margin-bottom: 5px; }
.param-val { font-family: 'Roboto Mono', monospace; color: var(--accent-blue); font-size: 13px; }
.param-slider { width: 100%; height: 5px; -webkit-appearance: none; appearance: none; background: rgba(255,255,255,0.08); border-radius: 4px; outline: none; cursor: pointer; }
.param-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%; background: var(--accent-blue); border: 2px solid rgba(255,255,255,0.15); cursor: pointer; transition: transform var(--transition-fast); }
.param-slider::-webkit-slider-thumb:hover { transform: scale(1.15); }
.param-slider:disabled { opacity: 0.4; cursor: not-allowed; }

.deep-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  padding: 4px 0;
}
.deep-toggle input { display: none; }
.deep-toggle-track {
  position: relative;
  width: 36px;
  height: 20px;
  background: rgba(255,255,255,0.08);
  border-radius: 10px;
  transition: background 250ms ease;
  flex-shrink: 0;
}
.deep-toggle-track .deep-toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--text-muted);
  transition: all 250ms ease;
}
.deep-toggle input:checked + .deep-toggle-track {
  background: rgba(59,130,246,0.3);
}
.deep-toggle input:checked + .deep-toggle-track .deep-toggle-thumb {
  left: 18px;
  background: var(--accent-blue);
  box-shadow: 0 0 8px rgba(59,130,246,0.4);
}
.deep-toggle-label {
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}
.deep-toggle-badge {
  font-size: 9px;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(59,130,246,0.1);
  color: var(--accent-blue);
  font-family: 'Roboto Mono', monospace;
}

.examples { display: flex; align-items: center; gap: 6px; width: 100%; }
.examples-label { font-size: 12px; color: var(--text-muted); flex-shrink: 0; }
.example-chip { flex: 1; font-size: 12px; padding: 5px 10px; background: rgba(255,255,255,0.03); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.06); border-radius: 20px; color: var(--text-muted); cursor: pointer; font-family: 'Exo', sans-serif; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; transition: all var(--transition-fast); }
.example-chip:hover:not(:disabled) { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.18); color: var(--text-secondary); }
.example-chip:disabled { opacity: 0.4; cursor: not-allowed; }

.history-section { width: 100%; margin-top: 4px; overflow: hidden; }
.history-header { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-muted); margin-bottom: 6px; }
.history-clear { margin-left: auto; background: none; border: none; color: var(--text-muted); font-size: 10px; font-family: 'Exo', sans-serif; cursor: pointer; padding: 2px 6px; border-radius: 4px; transition: color var(--transition-fast); }
.history-clear:hover { color: #f87171; }
.history-list { display: flex; flex-direction: column; gap: 3px; max-height: 140px; overflow-y: auto; scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.06) transparent; }
.history-item { display: flex; align-items: center; gap: 6px; width: 100%; padding: 6px 10px; background: rgba(255,255,255,0.02); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.04); border-radius: var(--radius-sm); cursor: pointer; font-family: 'Exo', sans-serif; text-align: left; transition: all var(--transition-fast); }
.history-item:hover { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.10); }
.history-item-title { flex: 1; font-size: 12px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.history-item-time { flex-shrink: 0; font-size: 10px; color: var(--text-muted); font-family: 'Roboto Mono', monospace; }

.hero-footer { display: flex; align-items: center; gap: 6px; padding: 12px 0; font-size: 11px; color: var(--text-muted); }
.footer-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--accent-blue); animation: pulse 2s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }

.right-panel {
  display: flex;
  flex-direction: column;
  padding: 24px 24px 24px 0;
  min-width: 0;
  min-height: 0;
  max-height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-count {
  font-size: 11px;
  background: rgba(255,255,255,0.06);
  padding: 1px 8px;
  border-radius: 10px;
  color: var(--text-muted);
}

.back-btn {
  background: none;
  border: 1px solid rgba(255,255,255,0.06);
  color: var(--text-secondary);
  font-size: 12px;
  font-family: 'Exo', sans-serif;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.back-btn:hover {
  background: rgba(255,255,255,0.06);
  color: var(--text-primary);
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.06) transparent;
}

.history-followup {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.followup-heading {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-blue);
}

.followup-form {
  display: flex;
  gap: 6px;
}

.followup-input {
  flex: 1;
  height: 32px;
  padding: 0 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 12px;
  font-family: 'Exo', sans-serif;
  outline: none;
  transition: all var(--transition-fast);
}

.followup-input:focus {
  border-color: rgba(59,130,246,0.35);
  background: rgba(255,255,255,0.07);
}

.followup-input::placeholder {
  color: var(--text-muted);
}

.followup-input:disabled {
  opacity: 0.5;
}

.followup-send {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(59,130,246,0.1);
  border: 1px solid rgba(59,130,246,0.2);
  border-radius: 6px;
  color: var(--accent-blue);
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.followup-send:hover:not(:disabled) {
  background: rgba(59,130,246,0.2);
  border-color: rgba(59,130,246,0.35);
}

.followup-send:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.followup-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.followup-error {
  display: block;
  font-size: 11px;
  color: #f87171;
}

.history-slide-enter-active,
.history-slide-leave-active {
  transition: opacity 300ms ease, max-height 300ms ease, margin 300ms ease, padding 300ms ease;
  overflow: hidden;
}
.history-slide-enter-from,
.history-slide-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
  padding-top: 0;
  padding-bottom: 0;
}
.history-slide-enter-to,
.history-slide-leave-from {
  opacity: 1;
  max-height: 200px;
}

.panel-enter-active {
  transition: opacity 400ms cubic-bezier(0, 0, 0.2, 1), transform 400ms cubic-bezier(0, 0, 0.2, 1);
}
.panel-leave-active {
  transition: opacity 350ms cubic-bezier(0, 0, 0.2, 1), transform 350ms cubic-bezier(0, 0, 0.2, 1);
}
.panel-enter-from,
.panel-leave-to {
  opacity: 0;
  transform: translateX(24px);
}

@media (max-width: 900px) {
  .app-layout { overflow-y: auto; align-items: stretch; }
  .layout-track { flex-direction: column; gap: 24px; max-width: none; transform: none; }
  .layout-track.shifted { gap: 24px; transform: none; }
  .layout-track.shifted .left-panel,
  .layout-track.shifted .right-panel { flex: none; width: 100%; }
  .left-panel { width: 100%; max-width: 100%; padding: 24px; }
  .right-panel { padding: 0 24px 24px; }
}
</style>
