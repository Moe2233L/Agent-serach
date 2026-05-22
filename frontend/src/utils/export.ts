import { marked } from 'marked'
import DOMPurify from 'dompurify'

function renderMarkdownToHtml(markdown: string): string {
  const rawHtml = marked.parse(markdown) as string
  let sanitized = DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr', 'ul', 'ol', 'li', 'a', 'strong', 'em', 'code', 'pre', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'img', 'span', 'div', 'del', 'sup', 'sub'],
    ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'id', 'src', 'alt', 'width', 'height'],
  })
  sanitized = sanitized.replace(/<a(?![^>]*target=)/g, '<a target="_blank" rel="noopener noreferrer"')
  return sanitized
}

function buildFullHtml(topic: string, bodyHtml: string): string {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${escapeHtml(topic)} - 研究报告</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Exo:wght@400;500;600;700&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Exo', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: #07070d;
    color: #f0fdfa;
    padding: 48px 32px;
    max-width: 900px;
    margin: 0 auto;
    -webkit-font-smoothing: antialiased;
  }
  .doc-title {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 8px;
    color: #f0fdfa;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(255,255,255,0.12);
  }
  .doc-meta {
    font-size: 13px;
    color: rgba(240,253,250,0.55);
    margin-bottom: 36px;
    font-family: 'Roboto Mono', monospace;
  }
  h1 { font-size: 22px; font-weight: 600; margin: 32px 0 16px; color: #f0fdfa; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); }
  h2 { font-size: 18px; font-weight: 600; margin: 28px 0 12px; color: #3b82f6; }
  h3 { font-size: 15px; font-weight: 600; margin: 20px 0 10px; color: #f0fdfa; }
  h4, h5, h6 { font-size: 14px; font-weight: 600; margin: 16px 0 8px; color: #f0fdfa; }
  p { margin-bottom: 12px; color: rgba(240,253,250,0.8); line-height: 1.8; }
  ul, ol { margin-bottom: 12px; padding-left: 24px; color: rgba(240,253,250,0.8); }
  li { margin-bottom: 4px; line-height: 1.7; }
  strong { color: #f0fdfa; font-weight: 600; }
  code { font-family: 'Roboto Mono', monospace; font-size: 12px; background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; color: #f97316; }
  pre { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; overflow-x: auto; margin-bottom: 16px; }
  pre code { background: none; padding: 0; color: rgba(240,253,250,0.8); font-size: 12px; line-height: 1.6; }
  blockquote { border-left: 3px solid #3b82f6; padding-left: 16px; margin: 12px 0; opacity: 0.85; color: rgba(240,253,250,0.8); }
  hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 24px 0; }
  a { color: #3b82f6; text-decoration: none; }
  a:hover { text-decoration: underline; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
  th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.08); font-size: 13px; }
  th { color: #f0fdfa; font-weight: 600; background: rgba(255,255,255,0.06); }
  td { color: rgba(240,253,250,0.8); }
  img { max-width: 100%; height: auto; border-radius: 8px; }
  @media print {
    body { background: #fff; color: #1a1a2e; padding: 20px; }
    h1, h2, h3, h4, h5, h6 { color: #1a1a2e; }
    h2 { color: #2563eb; }
    p, li, td { color: #333; }
    strong { color: #1a1a2e; }
    code { color: #c2410c; background: #f1f5f9; }
    pre { background: #f8fafc; border-color: #e2e8f0; }
    pre code { color: #333; }
    blockquote { opacity: 1; color: #475569; }
    a { color: #2563eb; }
    .doc-meta { color: #94a3b8; }
  }
</style>
</head>
<body>
<h1 class="doc-title">${escapeHtml(topic)}</h1>
<p class="doc-meta">生成日期：${new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })} | 由 Research Agent 生成</p>
${bodyHtml}
</body>
</html>`
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

export function downloadMarkdown(topic: string, markdown: string): void {
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${topic}_研究报告.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function downloadHtml(topic: string, markdown: string): void {
  const bodyHtml = renderMarkdownToHtml(markdown)
  const fullHtml = buildFullHtml(topic, bodyHtml)
  const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${topic}_研究报告.html`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function downloadPdf(topic: string, markdown: string): void {
  const bodyHtml = renderMarkdownToHtml(markdown)
  const fullHtml = buildFullHtml(topic, bodyHtml)
  const printWindow = window.open('', '_blank')
  if (!printWindow) {
    alert('无法打开打印窗口，请检查浏览器是否拦截了弹窗。')
    return
  }
  printWindow.document.write(fullHtml)
  printWindow.document.close()
  printWindow.focus()
  printWindow.onload = () => {
    printWindow.print()
    printWindow.onafterprint = () => {
      printWindow.close()
    }
  }
  setTimeout(() => {
    printWindow.print()
  }, 500)
}
