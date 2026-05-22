<template>
  <canvas ref="canvasRef" class="particle-canvas"></canvas>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

const canvasRef = ref<HTMLCanvasElement | null>(null)
const prefersReducedMotion = ref(false)

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  baseVx: number
  baseVy: number
  radius: number
  alpha: number
  glowAlpha: number
}

let particles: Particle[] = []
let animationId: number | null = null
let mouseX = -9999
let mouseY = -9999
let mouseActive = false
let canvasWidth = 0
let canvasHeight = 0

const PARTICLE_COUNT = 110
const CONNECTION_DIST = 140
const MOUSE_RADIUS = 80
const DRIFT_SPEED = 0.65
const MOUSE_FORCE = 0.08

function initParticles(w: number, h: number): Particle[] {
  return Array.from({ length: PARTICLE_COUNT }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    vx: (Math.random() - 0.5) * DRIFT_SPEED,
    vy: (Math.random() - 0.5) * DRIFT_SPEED,
    baseVx: (Math.random() - 0.5) * DRIFT_SPEED,
    baseVy: (Math.random() - 0.5) * DRIFT_SPEED,
    radius: 1.5 + Math.random() * 3.5,
    alpha: 0.15 + Math.random() * 0.45,
    glowAlpha: 0.08 + Math.random() * 0.2,
  }))
}

function resize() {
  const canvas = canvasRef.value
  if (!canvas) return
  const dpr = window.devicePixelRatio || 1
  const w = window.innerWidth
  const h = window.innerHeight
  canvasWidth = w
  canvasHeight = h
  canvas.width = w * dpr
  canvas.height = h * dpr
  canvas.style.width = `${w}px`
  canvas.style.height = `${h}px`
  const ctx = canvas.getContext('2d')
  if (ctx) ctx.scale(dpr, dpr)
  particles = initParticles(w, h)
}

function draw(ctx: CanvasRenderingContext2D) {
  ctx.clearRect(0, 0, canvasWidth, canvasHeight)

  for (const p of particles) {
    const dx = p.x - mouseX
    const dy = p.y - mouseY
    const dist = Math.sqrt(dx * dx + dy * dy)
    const inMouseZone = dist < MOUSE_RADIUS && mouseActive

    if (inMouseZone) {
      const force = (1 - dist / MOUSE_RADIUS) * MOUSE_FORCE
      p.vx += Math.sign(dx) * force
      p.vy += Math.sign(dy) * force
      p.vx *= 0.98
      p.vy *= 0.98
    } else {
      p.vx += (p.baseVx - p.vx) * 0.01
      p.vy += (p.baseVy - p.vy) * 0.01
    }

    p.x += p.vx
    p.y += p.vy

    if (p.x < 0) p.x = canvasWidth
    if (p.x > canvasWidth) p.x = 0
    if (p.y < 0) p.y = canvasHeight
    if (p.y > canvasHeight) p.y = 0

    const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.radius * 4)
    glow.addColorStop(0, `rgba(59, 130, 246, ${p.glowAlpha})`)
    glow.addColorStop(0.5, `rgba(129, 140, 248, ${p.glowAlpha * 0.5})`)
    glow.addColorStop(1, `rgba(59, 130, 246, 0)`)
    ctx.fillStyle = glow
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.radius * 4, 0, Math.PI * 2)
    ctx.fill()

    ctx.fillStyle = `rgba(240, 253, 250, ${p.alpha})`
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
    ctx.fill()
  }

  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const a = particles[i]
      const b = particles[j]
      const dx = a.x - b.x
      const dy = a.y - b.y
      const dist = dx * dx + dy * dy

      if (dist < CONNECTION_DIST * CONNECTION_DIST) {
        const alpha = (1 - Math.sqrt(dist) / CONNECTION_DIST) * 0.80
        ctx.strokeStyle = `rgba(148, 163, 184, ${alpha})`
        ctx.lineWidth = 0.5
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(b.x, b.y)
        ctx.stroke()
      }
    }
  }
}

function tick(ctx: CanvasRenderingContext2D) {
  if (!prefersReducedMotion.value) {
    draw(ctx)
  }
  animationId = requestAnimationFrame(() => tick(ctx))
}

function onMouseMove(e: MouseEvent) {
  mouseX = e.clientX
  mouseY = e.clientY
  mouseActive = true
}

function onMouseLeave() {
  mouseActive = false
  mouseX = -9999
  mouseY = -9999
}

onMounted(() => {
  prefersReducedMotion.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  resize()
  window.addEventListener('resize', resize)
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseleave', onMouseLeave)
  document.addEventListener('visibilitychange', onVisibilityChange)

  tick(ctx)
})

onBeforeUnmount(() => {
  if (animationId !== null) cancelAnimationFrame(animationId)
  window.removeEventListener('resize', resize)
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseleave', onMouseLeave)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

function onVisibilityChange() {
  if (document.hidden && animationId !== null) {
    cancelAnimationFrame(animationId)
    animationId = null
  } else if (!document.hidden && !prefersReducedMotion.value) {
    const canvas = canvasRef.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (ctx) tick(ctx)
  }
}
</script>

<style scoped>
.particle-canvas {
  position: fixed;
  inset: 0;
  z-index: 0;
  display: block;
  pointer-events: none;
  background:
    radial-gradient(ellipse 70% 55% at 20% 25%, rgba(37, 99, 235, 0.04) 0%, transparent 60%),
    radial-gradient(ellipse 60% 45% at 80% 75%, rgba(99, 102, 241, 0.03) 0%, transparent 50%),
    linear-gradient(180deg, #1e1f5f 0%, #262763 50%, #4c4c77 100%);
}


</style>
