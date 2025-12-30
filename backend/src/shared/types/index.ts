/**
 * @fileoverview 共享类型定义模块 (Shared Types)
 * 
 * 集中定义了后端系统使用的核心数据结构、接口规范和枚举常量。
 * 涵盖了用户模型、服务配置、API 协议、消息格式以及各 AI 服务的请求/响应类型。
 * 
 * 主要内容：
 * 1. 核心实体：User, UserProfile, LearningRecord, Session
 * 2. 服务配置：ServiceConfig, OrchestratorConfig, RouteRule, PipelineStep
 * 3. API 规范：APIRequest, APIResponse, ErrorCode
 * 4. AI 服务接口：OCR, ASR, TTS, LLM, Analysis 的请求与响应结构
 * 5. 消息协议：Message 接口及 TOPICS 常量
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

/**
 * 用户基础信息
 */
export interface User {
  id: string;
  username: string;
  email: string;
  language: string;
  createdAt: number;
  updatedAt: number;
}

/**
 * 用户学习画像
 * 记录用户在各个维度的能力水平
 */
export interface UserProfile {
  userId: string;
  vocabularyLevel: number;      // 词汇量等级 (0-100)
  grammarLevel: number;          // 语法掌握度 (0-100)
  pronunciationLevel: number;    // 发音准确度 (0-100)
  expressionLevel: number;       // 表达流利度 (0-100)
  overallLevel: number;          // 综合能力评分 (0-100)
  strongAreas: string[];         // 优势领域
  weakAreas: string[];           // 待提升领域
  updatedAt: number;
}

/**
 * 学习记录
 * 追踪用户的每一次学习活动
 */
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

/**
 * 系统错误代码枚举
 */
export enum ErrorCode {
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  AUTHORIZATION_ERROR = 'AUTHORIZATION_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE'
}

/**
 * 消息主题常量
 */
export const TOPICS = {
  ORCHESTRATOR: 'orchestrator',
  ASR: 'asr',
  TTS: 'tts',
  CHAT: 'chat',
  SYSTEM: 'system'
} as const;

/**
 * 会话状态
 */
export interface Session {
  id: string;
  userId?: string;
  peerId: string;
  capabilities?: string[];
  isAuthenticated: boolean;
  lastHeartbeat: number;
  createdAt: number;
  metadata?: any;
}

/**
 * 服务配置相关类型
 */

export type ServiceType = 'process' | 'http' | 'stream';

export interface HealthCheck {
  interval: number;           // 检查间隔 (ms)
  timeout: number;            // 超时时间 (ms)
  retries?: number;           // 最大重试次数
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
  endpoint?: string;          // HTTP 地址或本地 IPC 路径
  command?: string;           // 进程启动命令 (Process 类型)
  healthCheck: HealthCheck;
  warmup?: WarmupConfig;
  timeout?: number;
  retries?: number;
}

export interface RouteRule {
  pattern: string;            // 路由匹配模式 (如 svc/*, svc/llm)
  service?: string;           // 目标服务名称
  pipeline?: PipelineStep[];  // 处理流水线 (可选)
  timeout?: number;
  retry?: number;
}

export interface PipelineStep {
  service: string;
  inputField?: string;        // 输入参数映射
  outputField?: string;       // 输出结果映射
  condition?: (ctx: any) => boolean; // 执行条件
  errorHandler?: string;      // 错误处理策略
}

export interface OrchestratorConfig {
  services: Record<string, ServiceConfig>;
  routes: Record<string, RouteRule>;
}

/**
 * API 通用请求/响应格式
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
 * 特定服务的请求/响应定义
 */

// OCR (光学字符识别)
export interface OCRRequest {
  image: string;              // Base64 编码的图像数据
  format?: string;            // 图像格式 (jpg, png 等)
}

export interface OCRResponse {
  text: string;
  confidence: number;
  layout?: any;
}

// ASR (自动语音识别)
export interface ASRRequest {
  audio: Buffer | string;     // 音频数据 (Buffer 或 Base64)
  format?: string;            // 音频格式 (wav, mp3 等)
  language?: string;
}

export interface ASRResponse {
  text: string;
  confidence: number;
}

// TTS (文本转语音)
export interface TTSRequest {
  text: string;
  voice?: string;
  rate?: number;              // 语速调节
}

export interface TTSResponse {
  audio: Buffer;              // 生成的音频数据
  format: string;
}

// LLM (大语言模型)
export interface LLMRequest {
  prompt: string;
  history?: Message[];        // 对话历史
  task?: string;              // 任务类型
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
  dimension: string;          // 分析维度 ('vocabulary', 'grammar' 等)
  timeRange?: [number, number];
}

export interface AnalysisResponse {
  dimension: string;
  currentLevel: number;
  trend: number;              // 趋势: -1(下降), 0(平稳), 1(上升)
  recommendations: string[];
  visualization?: string;     // 可视化图表配置
}

// 消息接口 (用于模块间通信)
export interface Message {
  id: string;
  sessionId: string;
  peerId: string;
  topic: string;
  type: string;
  payload: any;
  metadata: any;
  sender?: string;
  timestamp?: number;
}
