// Dev backend: use 8001 by default to avoid port conflicts
var backend = 'http://127.0.0.1:8001';
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
