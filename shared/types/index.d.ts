/**
 * 用户相关数据结构
 */
export interface User {
    id: string;
    username: string;
    email: string;
    language: string;
    createdAt: number;
    updatedAt: number;
}
export interface UserProfile {
    userId: string;
    vocabularyLevel: number;
    grammarLevel: number;
    pronunciationLevel: number;
    expressionLevel: number;
    overallLevel: number;
    strongAreas: string[];
    weakAreas: string[];
    updatedAt: number;
}
export interface LearningRecord {
    id: string;
    userId: string;
    recordType: 'vocabulary' | 'essay' | 'dialogue' | 'analysis';
    content: {
        word?: string;
        text?: string;
        audio?: string;
        image?: string;
    };
    result?: {
        definition?: string;
        examples?: string[];
        score?: number;
        feedback?: string;
    };
    createdAt: number;
}
export declare enum ErrorCode {
    VALIDATION_ERROR = "VALIDATION_ERROR",
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR",
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR",
    NOT_FOUND = "NOT_FOUND",
    INTERNAL_ERROR = "INTERNAL_ERROR",
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
}
export declare const TOPICS: {
    readonly ORCHESTRATOR: "orchestrator";
    readonly ASR: "asr";
    readonly TTS: "tts";
    readonly CHAT: "chat";
    readonly SYSTEM: "system";
};
export interface Session {
    id: string;
    userId: string;
    createdAt: Date;
    lastActivity: Date;
    isActive: boolean;
}
/**
 * 服务配置
 */
export type ServiceType = 'process' | 'http' | 'stream';
export interface HealthCheck {
    interval: number;
    timeout: number;
    retries?: number;
}
export interface WarmupConfig {
    enabled: boolean;
    trigger: 'startup' | 'on-demand' | 'scheduled';
    timeout?: number;
    priority?: number;
}
export interface ServiceConfig {
    type: ServiceType;
    name: string;
    endpoint?: string;
    command?: string;
    healthCheck: HealthCheck;
    warmup?: WarmupConfig;
    timeout?: number;
    retries?: number;
}
export interface RouteRule {
    pattern: string;
    service?: string;
    pipeline?: PipelineStep[];
    timeout?: number;
    retry?: number;
}
export interface PipelineStep {
    service: string;
    inputField?: string;
    outputField?: string;
    condition?: (ctx: any) => boolean;
    errorHandler?: string;
}
export interface OrchestratorConfig {
    services: Record<string, ServiceConfig>;
    routes: Record<string, RouteRule>;
}
/**
 * API 请求/响应格式
 */
export interface APIRequest {
    action: string;
    data: any;
    metadata?: {
        timeout?: number;
        priority?: number;
    };
}
export interface APIResponse<T = any> {
    ok: boolean;
    code: number;
    message?: string;
    data?: T;
    error?: {
        code: string;
        message: string;
        details?: any;
    };
}
/**
 * 特定服务的请求/响应
 */
export interface OCRRequest {
    image: string;
    format?: string;
}
export interface OCRResponse {
    text: string;
    confidence: number;
    layout?: any;
}
export interface ASRRequest {
    audio: Buffer | string;
    format?: string;
    language?: string;
}
export interface ASRResponse {
    text: string;
    confidence: number;
}
export interface TTSRequest {
    text: string;
    voice?: string;
    rate?: number;
}
export interface TTSResponse {
    audio: Buffer;
    format: string;
}
export interface LLMRequest {
    prompt: string;
    history?: Message[];
    task?: string;
    maxTokens?: number;
    temperature?: number;
}
export interface LLMResponse {
    response: string;
    tokenUsage?: {
        prompt: number;
        completion: number;
    };
}
export interface AnalysisRequest {
    userId: string;
    dimension: string;
    timeRange?: [number, number];
}
export interface AnalysisResponse {
    dimension: string;
    currentLevel: number;
    trend: number;
    recommendations: string[];
    visualization?: string;
}
export interface Message {
    id: string;
    sessionId: string;
    peerId: string;
    topic: string;
    type: string;
    payload: any;
    metadata: any;
}
//# sourceMappingURL=index.d.ts.map