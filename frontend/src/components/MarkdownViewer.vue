<template>
  <div class="markdown-viewer" v-html="rendered"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  content: string
}>()

marked.setOptions({
  gfm: true,
  breaks: true,
})

const rendered = computed(() => {
  if (!props.content) return ''
  const html = marked.parse(props.content) as string
  // 确保所有链接在新窗口打开
  return html.replace(/<a(?![^>]*target="_blank")/g, '<a target="_blank" rel="noopener noreferrer"')
})
</script>

<style scoped>
.markdown-viewer {
  line-height: 1.8;
  color: var(--text-primary);
  font-size: 14px;
  overflow-y: auto;
  max-height: 60vh;
  padding-right: 4px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.1) transparent;
}

.markdown-viewer :deep(h1) {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--text-primary);
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.markdown-viewer :deep(h2) {
  font-size: 18px;
  font-weight: 600;
  margin-top: 28px;
  margin-bottom: 14px;
  color: var(--accent-blue);
}

.markdown-viewer :deep(h3) {
  font-size: 15px;
  font-weight: 600;
  margin-top: 20px;
  margin-bottom: 10px;
  color: var(--text-primary);
}

.markdown-viewer :deep(p) {
  margin-bottom: 12px;
  color: var(--text-secondary);
  line-height: 1.8;
}

.markdown-viewer :deep(ul),
.markdown-viewer :deep(ol) {
  margin-bottom: 12px;
  padding-left: 24px;
  color: var(--text-secondary);
}

.markdown-viewer :deep(li) {
  margin-bottom: 4px;
}

.markdown-viewer :deep(strong) {
  color: var(--text-primary);
  font-weight: 600;
}

.markdown-viewer :deep(code) {
  font-family: 'Roboto Mono', monospace;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--accent-orange);
}

.markdown-viewer :deep(pre) {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
  padding: 16px;
  overflow-x: auto;
  margin-bottom: 16px;
}

.markdown-viewer :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.markdown-viewer :deep(blockquote) {
  border-left: 3px solid var(--accent-blue);
  padding-left: 16px;
  margin: 12px 0;
  opacity: 0.8;
  color: var(--text-secondary);
}

.markdown-viewer :deep(hr) {
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  margin: 24px 0;
}

.markdown-viewer :deep(a) {
  color: var(--accent-blue);
  text-decoration: none;
  transition: opacity var(--transition-fast);
}

.markdown-viewer :deep(a:hover) {
  opacity: 0.8;
  text-decoration: underline;
}

/* 参考文献编号样式 */
.markdown-viewer :deep(h5),
.markdown-viewer :deep(h6) {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
  margin-top: 16px;
  margin-bottom: 8px;
}

.markdown-viewer :deep(ol) {
  padding-left: 24px;
  margin-bottom: 12px;
}

.markdown-viewer :deep(ol li) {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
  line-height: 1.6;
  word-break: break-all;
}

.markdown-viewer :deep(ol li a) {
  color: var(--accent-blue);
  font-size: 12px;
}

/* 正文中 [1] 引用样式 */
.markdown-viewer :deep(p) code {
  font-size: 12px;
  color: var(--accent-blue);
  background: rgba(59, 130, 246, 0.1);
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 600;
}

.markdown-viewer :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 16px;
}

.markdown-viewer :deep(th),
.markdown-viewer :deep(td) {
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 13px;
}

.markdown-viewer :deep(th) {
  color: var(--text-primary);
  font-weight: 600;
  background: rgba(255, 255, 255, 0.04);
}

.markdown-viewer :deep(td) {
  color: var(--text-secondary);
}
</style>
