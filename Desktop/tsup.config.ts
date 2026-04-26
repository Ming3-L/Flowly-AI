import { defineConfig } from 'tsup'

export default defineConfig({
  entry: ['src/main.ts'],
  format: ['cjs'],
  platform: 'node',
  target: 'node20',
  outDir: 'dist-electron',
  sourcemap: true,
  clean: true,
  external: ['electron'],
})

