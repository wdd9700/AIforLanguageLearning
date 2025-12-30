export type SKey = 'lmstudio' | 'whisper' | 'surya' | 'cosy';

export type SState = {
    status: 'stopped' | 'starting' | 'running' | 'error';
    message?: string;
    lastProbe?: number;
};

export type Ports = {
    lmstudio: number | null;
    whisper: number | null;
    surya: number | null;
    cosy: number | null;
    app?: number | null;
};

export type Config = {
    ports: Ports;
    // 兼容旧字段：theme/backendUrl 仍可能存在于老版本配置
    theme: 'system' | 'light' | 'dark';
    backendUrl: string;

    // 新字段：与渲染进程 AppConfig 对齐
    general?: {
        theme: 'dark' | 'light' | 'system';
        language: string;
        autoUpdate: boolean;
    };
    audio?: {
        inputDevice: string;
        outputDevice: string;
        volume: number;
    };
    ai?: {
        model: string;
        temperature: number;
        voice: string;
    };
    backend?: {
        url: string;
        wsUrl: string;
    };
    llmEndpoint?: string;
};
