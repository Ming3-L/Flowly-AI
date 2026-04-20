<template>
  <canvas ref="canvasRef" class="bg-canvas"></canvas>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const canvasRef = ref<HTMLCanvasElement | null>(null)
let animId: number | null = null

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')!

  const cfg = {
    gridSize: 32,
    spacing: 2,
    cubeSize: 36,
    rotX: -0.4,
    rotY: 0.7,
    scale: 1,
    minScale: 0.4,
    maxScale: 2.8,
    color: 'rgba(255,255,255',      // 适配深色背景，白色线条
    autoRotate: 0.0012,
    pulse: 0,
    pulseSpeed: 0.015,
    particleCount: 120,
    flowSpeed: 0.03,
    orbitCount: 6,
    nodeCount: 32,
  }

  let particles: { x: number; y: number; z: number; size: number; speed: number; pulse: number }[] = []
  let orbits: { radius: number; speed: number; angle: number }[] = []
  let nodes: { x: number; y: number; z: number; pulse: number }[] = []

  function initParticles() {
    particles = []
    for (let i = 0; i < cfg.particleCount; i++) {
      particles.push({
        x: (Math.random() - 0.5) * cfg.cubeSize * 1.8,
        y: (Math.random() - 0.5) * cfg.cubeSize * 1.8,
        z: (Math.random() - 0.5) * cfg.cubeSize * 1.8,
        size: Math.random() * 1.6 + 0.3,
        speed: Math.random() * 0.3 + 0.08,
        pulse: Math.random() * Math.PI * 2,
      })
    }
  }

  function initOrbits() {
    orbits = []
    for (let i = 0; i < cfg.orbitCount; i++) {
      orbits.push({ radius: 8 + i * 6, speed: 0.007 + i * 0.001, angle: Math.random() * Math.PI * 2 })
    }
  }

  function initNodes() {
    nodes = []
    for (let i = 0; i < cfg.nodeCount; i++) {
      nodes.push({
        x: (Math.random() - 0.5) * cfg.cubeSize * 1.4,
        y: (Math.random() - 0.5) * cfg.cubeSize * 0.4,
        z: (Math.random() - 0.5) * cfg.cubeSize * 1.4,
        pulse: Math.random() * Math.PI * 2,
      })
    }
  }

  function resize() {
    if (!canvas) return
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
  }

  function project(x: number, y: number, z: number): [number, number, number] {
    const cx = Math.cos(cfg.rotX), sx = Math.sin(cfg.rotX)
    const cy = Math.cos(cfg.rotY), sy = Math.sin(cfg.rotY)
    const rx = x * cy - z * sy
    const rz = z * cy + x * sy
    const ry = y * cx - rz * sx
    return [rx * cfg.gridSize * cfg.scale, ry * cfg.gridSize * cfg.scale, rz]
  }

  function drawCube() {
    const s = cfg.cubeSize
    const pts: [number, number, number][] = [
      [-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s],
      [-s, -s, s], [s, -s, s], [s, s, s], [-s, s, s],
    ]
    const edges = [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [0, 4], [1, 5], [2, 6], [3, 7]]
    ctx.lineWidth = 1
    ctx.strokeStyle = `${cfg.color},0.6)`
    edges.forEach(([a, b]) => {
      const [x1, y1] = project(...pts[a])
      const [x2, y2] = project(...pts[b])
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
    })
  }

  function drawGrid(pulse: number) {
    ctx.lineWidth = 0.35
    const s = cfg.cubeSize

    for (const zv of [-s, s]) {
      for (let a = -s; a <= s; a += cfg.spacing) {
        ctx.globalAlpha = 1 - Math.abs(zv) / s * 0.5
        ctx.strokeStyle = `${cfg.color},0.18)`
        ctx.beginPath()
        for (let b = -s; b <= s; b += cfg.spacing) {
          const [px, py] = project(a, b, zv)
          ctx.lineTo(px * pulse, py * pulse)
        }
        ctx.stroke()
        ctx.beginPath()
        for (let b = -s; b <= s; b += cfg.spacing) {
          const [px, py] = project(b, a, zv)
          ctx.lineTo(px * pulse, py * pulse)
        }
        ctx.stroke()
      }
    }

    for (const yv of [-s, s]) {
      for (let a = -s; a <= s; a += cfg.spacing) {
        ctx.globalAlpha = 1 - Math.abs(yv) / s * 0.5
        ctx.strokeStyle = `${cfg.color},0.18)`
        ctx.beginPath()
        for (let b = -s; b <= s; b += cfg.spacing) {
          const [px, py] = project(a, yv, b)
          ctx.lineTo(px * pulse, py * pulse)
        }
        ctx.stroke()
        ctx.beginPath()
        for (let b = -s; b <= s; b += cfg.spacing) {
          const [px, py] = project(b, yv, a)
          ctx.lineTo(px * pulse, py * pulse)
        }
        ctx.stroke()
      }
    }

    for (const xv of [-s, s]) {
      for (let a = -s; a <= s; a += cfg.spacing) {
        ctx.globalAlpha = 1 - Math.abs(xv) / s * 0.5
        ctx.strokeStyle = `${cfg.color},0.18)`
        ctx.beginPath()
        for (let b = -s; b <= s; b += cfg.spacing) {
          const [px, py] = project(xv, a, b)
          ctx.lineTo(px * pulse, py * pulse)
        }
        ctx.stroke()
        ctx.beginPath()
        for (let b = -s; b <= s; b += cfg.spacing) {
          const [px, py] = project(xv, b, a)
          ctx.lineTo(px * pulse, py * pulse)
        }
        ctx.stroke()
      }
    }

    ctx.globalAlpha = 1
  }

  function draw() {
    if (!canvas) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.save()
    ctx.translate(canvas.width / 2, canvas.height / 2)

    cfg.pulse += cfg.pulseSpeed
    const pulse = Math.sin(cfg.pulse) * 0.2 + 1
    cfg.rotY += cfg.autoRotate

    drawCube()
    drawGrid(pulse)

    // Orbits
    orbits.forEach(o => {
      o.angle += o.speed
      ctx.beginPath()
      ctx.arc(0, 0, o.radius * pulse, 0, Math.PI * 2)
      ctx.lineWidth = 0.6
      ctx.strokeStyle = `${cfg.color},0.25)`
      ctx.stroke()
    })

    // Nodes
    nodes.forEach(n => {
      n.pulse += 0.14
      const [px, py, rz] = project(n.x, n.y, n.z)
      const a = 1 - Math.abs(rz) / cfg.cubeSize
      const blink = (Math.sin(n.pulse) * 0.5 + 0.5)
      ctx.beginPath()
      ctx.arc(px * pulse, py * pulse, 1 + blink * 0.5, 0, Math.PI * 2)
      ctx.fillStyle = `${cfg.color},${a * (0.3 + blink * 0.5)})`
      ctx.fill()
    })

    // Node lines
    ctx.lineWidth = 0.3
    ctx.strokeStyle = `${cfg.color},0.12)`
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const d = Math.hypot(nodes[i].x - nodes[j].x, nodes[i].z - nodes[j].z)
        if (d < 8) {
          const [x1, y1] = project(nodes[i].x, nodes[i].y, nodes[i].z)
          const [x2, y2] = project(nodes[j].x, nodes[j].y, nodes[j].z)
          ctx.beginPath()
          ctx.moveTo(x1 * pulse, y1 * pulse)
          ctx.lineTo(x2 * pulse, y2 * pulse)
          ctx.stroke()
        }
      }
    }

    // Particles
    particles.forEach(p => {
      p.pulse += cfg.flowSpeed
      p.z += p.speed
      if (p.z > cfg.cubeSize) p.z = -cfg.cubeSize
      const [px, py, rz] = project(p.x, p.y, p.z)
      const size = p.size * (0.7 + Math.sin(p.pulse) * 0.4)
      const a = 1 - Math.abs(rz) / cfg.cubeSize
      ctx.beginPath()
      ctx.arc(px * pulse, py * pulse, size, 0, Math.PI * 2)
      ctx.fillStyle = `${cfg.color},${a * 0.8})`
      ctx.fill()
    })

    // Center glow
    const g = 24 + Math.sin(cfg.pulse * 1.6) * 5
    ctx.beginPath()
    ctx.arc(0, 0, g, 0, Math.PI * 2)
    const grd = ctx.createRadialGradient(0, 0, 0, 0, 0, g)
    grd.addColorStop(0, `${cfg.color},0.25)`)
    grd.addColorStop(1, `${cfg.color},0)`)
    ctx.fillStyle = grd
    ctx.fill()

    // Scan ring
    const scan = (Math.sin(cfg.pulse * 2) * 0.5 + 0.5)
    ctx.lineWidth = 0.7
    ctx.strokeStyle = `${cfg.color},${0.2 + scan * 0.15})`
    const s = cfg.cubeSize * 0.7 * pulse
    ctx.strokeRect(-s, -s, s * 2, s * 2)

    ctx.restore()
    animId = requestAnimationFrame(draw)
  }

  initParticles()
  initOrbits()
  initNodes()
  resize()
  window.addEventListener('resize', resize)
  draw()
})

onUnmounted(() => {
  if (animId !== null) cancelAnimationFrame(animId)
  window.removeEventListener('resize', () => {})
})
</script>

<style scoped>
.bg-canvas {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}
</style>
