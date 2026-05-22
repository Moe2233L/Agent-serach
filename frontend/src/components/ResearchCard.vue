<template>
  <div class="research-card" :class="{ completed: isCompleted, errored: !!error }" @click="toggleCollapse">
    <div class="card-header">
      <div class="card-title-group">
        <span class="card-status-dot" :class="statusClass"></span>
        <span class="card-title">{{ topic }}</span>
      </div>
      <div class="card-header-actions">
        <button v-if="showCancel" class="card-cancel" @click.stop="$emit('cancel')" title="取消研究">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f87171" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        </button>
        <button v-else-if="!isHistory" class="card-close" @click.stop="$emit('remove')" title="关闭">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
        <button class="card-toggle" :class="{ rotated: !collapsed }" @click.stop="toggleCollapse" title="折叠/展开">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
        </button>
      </div>
    </div>

    <template v-if="!isHistory">
      <div class="progress-section">
        <div class="progress-track">
          <div class="progress-bar-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <div class="progress-label">
          <span>整体进度</span>
          <span class="progress-value">{{ progressPercent }}%</span>
        </div>
      </div>
    </template>

    <div v-if="error" class="card-error">{{ error }}</div>

    <div ref="bodyRef" class="collapsible-body" :class="{ collapsed }">
      <div class="collapsible-inner">
        <template v-if="!isHistory">
          <div class="step-bar">
            <div v-for="(step, i) in steps" :key="i" class="step" :class="stepClass(i)">
              <div class="step-dot-row">
                <div class="step-line" :class="{ filled: i <= currentPhase }"></div>
                <div class="step-dot"></div>
                <div class="step-line" :class="{ filled: i < currentPhase }"></div>
              </div>
              <span class="step-label">{{ step }}</span>
            </div>
          </div>

          <div v-if="currentPhase === 0 && (!subtasks || subtasks.length === 0)" class="skeleton">
            <div class="skeleton-line skeleton-line-title"></div>
            <div class="skeleton-line skeleton-line-text"></div>
            <div class="skeleton-line skeleton-line-text skeleton-line-short"></div>
            <div class="skeleton-chips">
              <div class="skeleton-chip"></div>
              <div class="skeleton-chip"></div>
              <div class="skeleton-chip"></div>
            </div>
          </div>

          <div v-if="subtasks && subtasks.length" class="subtask-compact">
            <div v-for="s in subtasks" :key="s.id" class="subtask-chip" :class="s.status">
              <svg v-if="s.status === 'completed'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5"><path d="M8 12l3 3 5-5"/></svg>
              <svg v-else-if="s.status === 'searching' || s.status === 'summarizing'" class="chip-spin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><circle cx="12" cy="12" r="10" stroke-dasharray="31.4 31.4" stroke-linecap="round"/></svg>
              <svg v-else width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity="0.25"/></svg>
              <span class="subtask-chip-label">{{ s.title }}</span>
              <span v-if="s.iteration && s.iteration > 1" class="subtask-iteration">({{ s.iteration }})</span>
              <span v-if="s.status === 'completed' && getSubtaskScore(s.id)" class="subtask-score" :class="scoreVariant(getSubtaskScore(s.id))">{{ getSubtaskScore(s.id) }}</span>
            </div>
          </div>
          <div v-if="reportRewriting" class="phase-message rewriting-msg">
            <span class="phase-spinner"></span>
            <span>正在根据质量评审优化报告...</span>
          </div>

          <div v-if="currentPhase >= 2" class="phase-message">
            <span v-if="currentPhase === 2" class="phase-spinner"></span>
            <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <span>{{ currentPhase === 2 ? '正在生成研究报告...' : '研究报告已生成' }}</span>
          </div>

          <div ref="logRef" class="log-list" v-if="logs && logs.length">
            <div v-for="(log, i) in logs" :key="i" class="log-line">
              <span class="log-phase-tag" :class="log.phase">{{ log.phaseLabel }}</span>
              <span class="log-msg">{{ log.message }}</span>
            </div>
          </div>
        </template>

        <Transition name="fade">
          <div v-if="report" class="report-area" @click.stop>
            <div class="report-bar">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
              <span>研究报告</span>
              <button class="download-btn" @click.stop="downloadReport">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                下载
              </button>
            </div>
            <MarkdownViewer :content="report" />
            <div v-if="!isHistory && reportCriticFeedback" class="critic-section">
              <div class="critic-header" @click="toggleCritic">
                <div class="critic-header-left">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                  <span>质量评审</span>
                </div>
                <div class="critic-header-right">
                  <span class="critic-badge" :class="reportScoreVariant">{{ reportOverallScore }}/10</span>
                  <svg class="critic-chevron" :class="{ rotated: criticOpen }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
                </div>
              </div>
              <div v-if="criticOpen" class="critic-body">
                <div class="critic-dimensions">
                  <div v-for="(val, key) in reportCriticFeedback.dimensions" :key="key" class="critic-dim-item">
                    <span class="critic-dim-label">{{ dimLabel(key) }}</span>
                    <div class="critic-dim-bar-track">
                      <div class="critic-dim-bar-fill" :class="scoreVariant(val)" :style="{ width: val * 10 + '%' }"></div>
                    </div>
                    <span class="critic-dim-val" :class="scoreVariant(val)">{{ val }}/10</span>
                  </div>
                </div>
                <div v-if="reportCriticFeedback.strengths.length" class="critic-section-item">
                  <div class="critic-section-title positive">优势</div>
                  <div v-for="(s, i) in reportCriticFeedback.strengths" :key="i" class="critic-item">✓ {{ s }}</div>
                </div>
                <div v-if="reportCriticFeedback.weaknesses.length" class="critic-section-item">
                  <div class="critic-section-title negative">不足</div>
                  <div v-for="(w, i) in reportCriticFeedback.weaknesses" :key="i" class="critic-item">✗ {{ w }}</div>
                </div>
                <div v-if="reportCriticFeedback.suggestions.length" class="critic-section-item">
                  <div class="critic-section-title suggestion">改进建议</div>
                  <div v-for="(s, i) in reportCriticFeedback.suggestions" :key="i" class="critic-item">→ {{ s }}</div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import MarkdownViewer from './MarkdownViewer.vue'
import type { SubtaskState, LogState, CriticFeedback } from '../types/research'

const props = defineProps<{
  topic: string
  subtasks?: SubtaskState[]
  logs?: LogState[]
  report?: string
  status?: string
  error?: string
  isHistory?: boolean
  subtaskCriticFeedback?: Record<number, CriticFeedback>
  reportCriticFeedback?: CriticFeedback | null
  reportRewriting?: boolean
}>()

const emit = defineEmits<{
  remove: []
  cancel: []
  download: [topic: string, content: string]
}>()

const logRef = ref<HTMLElement | null>(null)
const bodyRef = ref<HTMLElement | null>(null)
const collapsed = ref(false)

watch(() => props.isHistory, (val) => {
  if (val) collapsed.value = true
}, { immediate: true })

const bodyObserver = ref<MutationObserver | null>(null)

onMounted(() => {
  if (bodyRef.value) {
    bodyObserver.value = new MutationObserver(() => {
        if (!collapsed.value) {
          bodyRef.value!.style.maxHeight = bodyRef.value!.scrollHeight + 40 + 'px'
        }
      })
    bodyObserver.value.observe(bodyRef.value, {
      childList: true,
      subtree: true,
      characterData: true,
    })
  }
})

onBeforeUnmount(() => {
  bodyObserver.value?.disconnect()
})

function toggleCollapse() {
  const el = bodyRef.value
  if (!el) {
    collapsed.value = !collapsed.value
    return
  }

  if (collapsed.value) {
    collapsed.value = false
    const h = el.scrollHeight
    el.style.maxHeight = h + 40 + 'px'
  } else {
    const h = el.scrollHeight
    el.style.maxHeight = h + 40 + 'px'
    requestAnimationFrame(() => {
      el.style.maxHeight = '0px'
    })
    collapsed.value = true
  }
}

watch(() => props.report, async () => {
  if (bodyRef.value && !collapsed.value) {
    await nextTick()
    bodyRef.value.style.maxHeight = bodyRef.value.scrollHeight + 40 + 'px'
  }
})

const progressPercent = computed(() => {
  if (props.status === 'completed') return 100
  if (props.report) return 92
  const subtasks = props.subtasks || []
  const total = subtasks.length
  if (total === 0) {
    if (props.status === 'planning' || !props.status) return 3
    return 8
  }
  const completed = subtasks.filter(s => s.status === 'completed').length
  const error = subtasks.filter(s => s.status === 'error').length
  const active = subtasks.filter(s => s.status === 'searching' || s.status === 'summarizing').length
  const done = completed + error
  if (done === total) return 75
  if (active > 0) {
    const perSubtask = 60 / total
    const base = 10
    const activeProgress = active > 0 ? perSubtask * 0.5 : 0
    return Math.round(base + done * perSubtask + activeProgress)
  }
  const perSubtask = 60 / total
  return Math.round(10 + done * perSubtask)
})

const steps = ['规划', '执行', '报告', '完成']

const currentPhase = computed(() => {
  if (props.status === 'completed') return 3
  if (props.status === 'reporting' || props.status === 'writing' || props.report) return 2
  if (props.status === 'executing' || props.status === 'searching' || props.status === 'summarizing') return 1
  if (props.subtasks?.some(s => s.status !== 'pending')) return 1
  return 0
})

function stepClass(i: number) {
  if (i < currentPhase.value) return 'step-completed'
  if (i === currentPhase.value) {
    if (currentPhase.value === 3) return 'step-completed'
    return 'step-active'
  }
  return 'step-future'
}

const isCompleted = computed(() => props.status === 'completed')

const showCancel = computed(() =>
  !props.isHistory && props.status !== 'completed' && props.status !== 'error'
)

const statusClass = computed(() => {
  if (props.status === 'error') return 'error'
  if (props.isHistory) return 'history'
  if (props.status === 'completed') return 'completed'
  if (props.subtasks?.some(s => s.status === 'searching' || s.status === 'summarizing')) return 'running'
  return 'pending'
})

watch(() => props.logs?.length, async () => {
  await nextTick()
  if (logRef.value) {
    logRef.value.scrollTop = logRef.value.scrollHeight
  }
})

function downloadReport() {
  if (!props.report) return
  const blob = new Blob([props.report], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.topic}_研究报告.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const criticOpen = ref(false)

function toggleCritic() {
  criticOpen.value = !criticOpen.value
}

const reportOverallScore = computed(() => props.reportCriticFeedback?.overall_score ?? 0)

const reportScoreVariant = computed(() => scoreVariant(reportOverallScore.value))

function getSubtaskScore(id: number): number {
  return props.subtaskCriticFeedback?.[id]?.overall_score ?? 0
}

function scoreVariant(val: number): string {
  if (val >= 8) return 'score-high'
  if (val >= 6) return 'score-medium'
  return 'score-low'
}

function dimLabel(key: string): string {
  const labels: Record<string, string> = {
    structure: '结构',
    depth: '深度',
    citation_accuracy: '引用',
    readability: '可读性',
    completeness: '完整性',
    relevance: '相关性',
    clarity: '清晰度',
    citation_quality: '引用质量',
  }
  return labels[key] || key
}
</script>

<style scoped>
.research-card {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all var(--transition-smooth);
  animation: cardMount 500ms cubic-bezier(0, 0, 0.2, 1);
  overflow: hidden;
  min-width: 0;
}

@keyframes cardMount {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.research-card.completed {
  border-color: rgba(59, 130, 246, 0.12);
  background: rgba(59, 130, 246, 0.02);
}

.research-card.errored {
  border-color: rgba(248, 113, 113, 0.15);
  background: rgba(248, 113, 113, 0.02);
}

.card-error {
  font-size: 12px;
  color: #f87171;
  padding: 6px 10px;
  background: rgba(248, 113, 113, 0.06);
  border: 1px solid rgba(248, 113, 113, 0.1);
  border-radius: var(--radius-sm);
  font-family: 'Roboto Mono', monospace;
  word-break: break-all;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
}

.card-header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.card-toggle {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.03);
  border: none;
  border-radius: 6px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.card-toggle:hover {
  background: rgba(255,255,255,0.08);
  color: var(--text-secondary);
}

.card-toggle.rotated svg {
  transform: rotate(180deg);
}

.card-toggle svg {
  transition: transform 300ms ease;
}

.card-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.card-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.card-status-dot.pending { background: var(--text-muted); }
.card-status-dot.running { background: var(--accent-blue); animation: pulse 1.2s ease-in-out infinite; }
.card-status-dot.completed { background: var(--accent-blue); }
.card-status-dot.error { background: #f87171; }
.card-status-dot.history { background: var(--text-muted); }

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-close {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.03);
  border: none;
  border-radius: 6px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.card-close:hover {
  background: rgba(255,255,255,0.08);
  color: var(--text-secondary);
}

.card-cancel {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(248,113,113,0.08);
  border: 1px solid rgba(248,113,113,0.15);
  border-radius: 6px;
  color: #f87171;
  cursor: pointer;
  transition: all var(--transition-fast);
  animation: cancelPulse 2s ease-in-out infinite;
}

.card-cancel:hover {
  background: rgba(248,113,113,0.18);
  border-color: rgba(248,113,113,0.3);
}

@keyframes cancelPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(248,113,113,0.15); }
  50% { box-shadow: 0 0 0 4px rgba(248,113,113,0.05); }
}

.collapsible-body {
  overflow: hidden;
  transition: max-height 450ms cubic-bezier(0, 0, 0.2, 1), opacity 300ms ease;
  opacity: 1;
}

.collapsible-body.collapsed {
  opacity: 0;
  max-height: 0;
}

.collapsible-inner {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 1px;
}

.step-bar {
  display: flex;
  align-items: flex-start;
  gap: 0;
  width: 100%;
  padding: 4px 0;
}

.step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.step-dot-row {
  display: flex;
  align-items: center;
  width: 100%;
}

.step-line {
  flex: 1;
  height: 2px;
  background: rgba(255,255,255,0.08);
  transition: background 400ms ease;
}

.step:first-child .step-line:first-child { visibility: hidden; }
.step:last-child .step-line:last-child { visibility: hidden; }

.step-line.filled {
  background: var(--accent-blue);
}

.step-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  transition: all 400ms ease;
}

.step-completed .step-dot {
  background: var(--accent-blue);
  box-shadow: 0 0 6px rgba(59,130,246,0.4);
}

.step-active .step-dot {
  background: var(--accent-blue);
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
  animation: stepPulse 1.5s ease-in-out infinite;
}

.step-future .step-dot {
  background: rgba(255,255,255,0.12);
}

@keyframes stepPulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(59,130,246,0.15); }
  50% { box-shadow: 0 0 0 6px rgba(59,130,246,0.06); }
}

.step-label {
  font-size: 10px;
  color: var(--text-muted);
  transition: color 400ms ease;
  white-space: nowrap;
}

.step-completed .step-label { color: var(--accent-blue); }
.step-active .step-label { color: var(--text-secondary); }

.progress-track {
  position: relative;
  width: 100%;
  height: 8px;
  background: rgba(255,255,255,0.06);
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan));
  border-radius: 4px;
  transition: width 500ms cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 10px rgba(59,130,246,0.35);
}

.progress-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'Roboto Mono', monospace;
}

.progress-value {
  font-size: 13px;
  font-weight: 700;
  color: var(--accent-blue);
}

.progress-section {
  flex-shrink: 0;
}

/* --- Skeleton --- */
.skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px 0;
}

.skeleton-line {
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.10) 50%, rgba(255,255,255,0.04) 75%);
  background-size: 200% 100%;
  animation: skeletonShimmer 1.5s ease-in-out infinite;
}

.skeleton-line-title {
  width: 60%;
  height: 16px;
}

.skeleton-line-text {
  width: 100%;
}

.skeleton-line-short {
  width: 45%;
}

.skeleton-chips {
  display: flex;
  gap: 6px;
  margin-top: 2px;
}

.skeleton-chip {
  width: 90px;
  height: 24px;
  border-radius: 6px;
  background: linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.03) 75%);
  background-size: 200% 100%;
  animation: skeletonShimmer 1.5s ease-in-out infinite 0.2s;
}

@keyframes skeletonShimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.phase-message {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'Roboto Mono', monospace;
}

.phase-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.1);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

.subtask-compact {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.subtask-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 6px;
  font-size: 11px;
  font-family: 'Roboto Mono', monospace;
  transition: all 300ms ease;
}

.subtask-chip.completed {
  border-color: rgba(59,130,246,0.15);
  background: rgba(59,130,246,0.04);
}

.subtask-chip.searching,
.subtask-chip.summarizing {
  border-color: rgba(59,130,246,0.15);
}

.subtask-chip-label {
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.subtask-chip.completed .subtask-chip-label {
  color: var(--text-muted);
}

.subtask-iteration {
  font-size: 9px;
  color: var(--accent-blue);
  font-weight: 600;
  flex-shrink: 0;
}

.chip-spin {
  animation: spin 1.2s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.log-list {
  max-height: 100px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.06) transparent;
}

.log-line {
  display: flex;
  gap: 6px;
  font-size: 11px;
  font-family: 'Roboto Mono', monospace;
}

.log-phase-tag {
  font-size: 10px;
  padding: 0 4px;
  border-radius: 3px;
  flex-shrink: 0;
  font-weight: 500;
}

.log-phase-tag.planning { background: rgba(139,92,246,0.10); color: #a78bfa; }
.log-phase-tag.executing { background: rgba(245,158,11,0.10); color: #fbbf24; }
.log-phase-tag.reporting { background: rgba(59,130,246,0.10); color: var(--accent-blue); }

.log-msg {
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.report-area {
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 12px;
}

.report-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-orange);
  margin-bottom: 8px;
}

.download-btn {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: rgba(255,255,255,0.04);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 11px;
  font-family: 'Exo', sans-serif;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.download-btn:hover {
  background: rgba(255,255,255,0.08);
  color: var(--text-primary);
  border-color: rgba(255,255,255,0.15);
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 300ms ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.rewriting-msg {
  animation: fadeInOut 1.5s ease-in-out infinite;
}

@keyframes fadeInOut {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.subtask-score {
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 4px;
  flex-shrink: 0;
  margin-left: auto;
}

.subtask-score.score-high {
  color: #34d399;
  background: rgba(52, 211, 153, 0.1);
}

.subtask-score.score-medium {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.1);
}

.subtask-score.score-low {
  color: #f87171;
  background: rgba(248, 113, 113, 0.1);
}

.critic-section {
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  margin-top: 12px;
  padding-top: 8px;
}

.critic-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  user-select: none;
}

.critic-header:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
}

.critic-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.critic-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.critic-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
}

.critic-badge.score-high {
  color: #34d399;
  background: rgba(52, 211, 153, 0.1);
}

.critic-badge.score-medium {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.1);
}

.critic-badge.score-low {
  color: #f87171;
  background: rgba(248, 113, 113, 0.1);
}

.critic-chevron {
  transition: transform 300ms ease;
  color: var(--text-muted);
}

.critic-chevron.rotated {
  transform: rotate(180deg);
}

.critic-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 8px 4px;
  animation: criticSlideIn 300ms ease;
}

@keyframes criticSlideIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.critic-dimensions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.critic-dim-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.critic-dim-label {
  font-size: 10px;
  color: var(--text-muted);
  width: 56px;
  flex-shrink: 0;
  text-align: right;
}

.critic-dim-bar-track {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2px;
  overflow: hidden;
}

.critic-dim-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 500ms cubic-bezier(0.4, 0, 0.2, 1);
}

.critic-dim-bar-fill.score-high {
  background: #34d399;
}

.critic-dim-bar-fill.score-medium {
  background: #fbbf24;
}

.critic-dim-bar-fill.score-low {
  background: #f87171;
}

.critic-dim-val {
  font-size: 9px;
  font-weight: 600;
  width: 28px;
  text-align: right;
  flex-shrink: 0;
  font-family: 'Roboto Mono', monospace;
}

.critic-dim-val.score-high { color: #34d399; }
.critic-dim-val.score-medium { color: #fbbf24; }
.critic-dim-val.score-low { color: #f87171; }

.critic-section-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.critic-section-title {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
}

.critic-section-title.positive { color: #34d399; }
.critic-section-title.negative { color: #f87171; }
.critic-section-title.suggestion { color: var(--accent-blue); }

.critic-item {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.5;
  padding: 2px 0;
}
</style>
