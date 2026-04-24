// Dev backend: default aligns with docs/backend runserver port (8000).
// Override via VITE_DEV_BACKEND, e.g. http://127.0.0.1:8001
var backend = process.env.VITE_DEV_BACKEND || 'http://127.0.0.1:8000';
export var devServerProxy = {
    '/api': {
        target: backend,
        changeOrigin: true,
        secure: false,
    },
    '/ws': {
        target: backend,
        changeOrigin: true,
        secure: false,
        ws: true,
    },
};
