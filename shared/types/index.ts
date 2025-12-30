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
  vocabularyLevel: number;      // 0-100
  grammarLevel: number;          // 0-100
  pronunciationLevel: number;    // 0-100
  expressionLevel: number;       // 0-100
  overallLevel: number;          // 0-100
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

export enum ErrorCode {
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  AUTHORIZATION_ERROR = 'AUTHORIZATION_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE'
}

export const TOPICS = {
  ORCHESTRATOR: 'orchestrator',
  ASR: 'asr',
  TTS: 'tts',
  CHAT: 'chat',
  SYSTEM: 'system'
} as const;

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
  interval: number;           // 检查间隔 (ms)
  timeout: number;            // 超时时间 (ms)
  retries?: number;           // 重试次数
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
  endpoint?: string;          // HTTP 或 local IPC 地址
  command?: string;           // 进程启动命令
  healthCheck: HealthCheck;
  warmup?: WarmupConfig;
  timeout?: number;
  retries?: number;
}

export interface RouteRule {
  pattern: string;            // 主题模式 (svc/*, svc/llm, 等)
  service?: string;           // 对应服务名
  pipeline?: PipelineStep[];  // 或流水线
  timeout?: number;
  retry?: number;
}

export interface PipelineStep {
  service: string;
  inputField?: string;        // 参数映射
  outputField?: string;       // 结果映射
  condition?: (ctx: any) => boolean;
  errorHandler?: string;      // 错误处理策略
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

// OCR
export interface OCRRequest {
  image: string;              // Base64 编码
  format?: string;            // jpg, png, etc
}

export interface OCRResponse {
  text: string;
  confidence: number;
  layout?: any;
}

// ASR
export interface ASRRequest {
  audio: Buffer | string;     // 音频数据或 Base64
  format?: string;            // wav, mp3, etc
  language?: string;
}

export interface ASRResponse {
  text: string;
  confidence: number;
}

// TTS
export interface TTSRequest {
  text: string;
  voice?: string;
  rate?: number;              // 语速
}

export interface TTSResponse {
  audio: Buffer;              // 音频数据
  format: string;
}

// LLM
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

// 学情分析
export interface AnalysisRequest {
  userId: string;
  dimension: string;          // 'vocabulary', 'grammar', etc
  timeRange?: [number, number];
}

export interface AnalysisResponse {
  dimension: string;
  currentLevel: number;
  trend: number;              // -1: 下降, 0: 平稳, 1: 上升
  recommendations: string[];
  visualization?: string;     // 图表数据
}

// 消息接口（用于导入）
export interface Message {
  id: string;
  sessionId: string;
  peerId: string;
  topic: string;
  type: string;
  payload: any;
  metadata: any;
}
