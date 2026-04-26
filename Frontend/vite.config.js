import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';
import { devServerProxy } from './src/config/vite-dev-proxy';
// https://vitejs.dev/config/
export default defineConfig({
    plugins: [vue()],
    // GitHub Pages 部署时需要设置为 "/<repo>/"；默认 "/" 适配本地与自定义域名。
    // 在 CI 中通过环境变量 VITE_PUBLIC_BASE_PATH 注入即可，无需改代码。
    base: process.env.VITE_PUBLIC_BASE_PATH || '/',
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src'),
        },
    },
    server: {
        port: 5173,
        host: true,
        proxy: devServerProxy,
    },
    build: {
        outDir: 'dist',
        sourcemap: false,
        rollupOptions: {
            output: {
                manualChunks: {
                    'element-plus': ['element-plus'],
                    'vue-vendor': ['vue', 'vue-router', 'pinia'],
                },
            },
        },
    },
});
