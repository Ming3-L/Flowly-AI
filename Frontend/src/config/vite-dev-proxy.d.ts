/**
 * Vite 开发服务器代理（集中配置，供 vite.config 引用）。
 */
import type { ProxyOptions } from 'vite';
export declare const devServerProxy: Record<string, string | ProxyOptions>;
