/**
 * @fileoverview 软总线消息协议定义 (Message Protocol)
 * 
 * 定义了前后端及服务间通信的统一消息格式。
 * 规范了消息的结构、类型、元数据、有效负载以及系统预定义的主题和错误码。
 * 
 * 主要内容：
 * 1. 消息结构：Message, Payload, MessageMetadata
 * 2. 消息类型：Request, Response, Stream, PubSub
 * 3. 主题常量 (TOPICS)：定义了服务、流水线、学习、认证和系统管理的主题
 * 4. 错误码 (ErrorCode)：标准化的系统错误代码及默认消息
 * 
 * @author GitHub Copilot
 * @copyright 2024 AiforForeignLanguageLearning
 */

export type MessageType = 'request' | 'response' | 'stream' | 'pubsub' | 'error';
export type PayloadType = 'text' | 'image' | 'audio' | 'binary' | 'json';
export type Encoding = 'utf8' | 'base64' | 'binary';

/**
 * 消息有效负载 (Payload)
 * 承载实际的业务数据
 */
export interface Payload {
  data: any;                 // 实际数据内容
  type: PayloadType;         // 数据类型
  encoding: Encoding;        // 编码方式
  size: number;              // 数据大小 (字节)
  chunkIndex?: number;       // 分片索引 (用于大文件传输)
  totalChunks?: number;      // 总分片数
}

/**
 * 消息元数据 (Metadata)
 * 包含消息的上下文信息，用于追踪和控制
 */
export interface MessageMetadata {
  timestamp: number;         // 发送时间戳
  userId?: string;           // 发起请求的用户 ID
  requestId: string;         // 请求追踪 ID (Trace ID)
  timeout: number;           // 超时时间 (ms)
  retries?: number;          // 已重试次数
}

/**
 * 统一消息格式
 * 所有通过软总线传输的消息都必须遵循此结构
 */
export interface Message {
  id: string;                // 消息唯一 ID (UUID)
  sessionId: string;         // 会话 ID (关联一次交互)
  peerId: string;            // 发送方节点 ID
  topic: string;             // 消息主题 (路由键)
  type: MessageType;         // 消息类型
  payload: Payload;          // 消息体
  metadata: MessageMetadata; // 元数据
  signature?: string;        // Ed25519 数字签名 (用于验证完整性)
}

/**
 * 响应消息
 * 对请求消息的回复
 */
export interface ResponseMessage extends Message {
  type: 'response';
  status: 'success' | 'error';
  code: number;              // 状态码
  message?: string;          // 状态描述
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}

/**
 * 流式消息
 * 用于音频流、视频流或大文件传输
 */
export interface StreamMessage extends Message {
  type: 'stream';
  isEnd?: boolean;           // 标记流是否结束
}

/**
 * 发布/订阅消息
 * 用于广播通知或事件推送
 */
export interface PubSubMessage extends Message {
  type: 'pubsub';
  subscribers?: number;      // 当前订阅者数量 (可选)
}

/**
 * 系统预定义主题常量
 */
export const TOPICS = {
  // 核心 AI 服务请求
  SERVICE: {
    OCR: 'svc/ocr',
    ASR: 'svc/asr',
    TTS: 'svc/tts',
    LLM: 'svc/llm',
  },
  
  // 复合服务流水线
  PIPELINE: {
    OCR_TO_LLM: 'svc/ocr-to-llm',
    ASR_TO_LLM: 'svc/asr-to-llm',
  },
  
  // 学习记录与分析
  LEARNING: {
    RECORD: 'learning/record',
    PROFILE: 'learning/profile',
    ANALYSIS: 'learning/analysis',
  },
  
  // 用户认证与授权
  AUTH: {
    LOGIN: 'auth/login',
    LOGOUT: 'auth/logout',
    REFRESH: 'auth/refresh',
  },
  
  // 系统管理与监控
  SYSTEM: {
    HEARTBEAT: 'system/heartbeat',
    DISCOVER: 'system/discover',
    STATUS: 'system/status',
  },
};

/**
 * 系统错误代码定义
 */
export const ErrorCode = {
  OK: 0,
  UNKNOWN_ERROR: 1000,
  TIMEOUT: 1001,
  INVALID_MESSAGE: 1002,
  
  UNAUTHORIZED: 2000,
  INVALID_TOKEN: 2001,
  SESSION_EXPIRED: 2002,
  
  SERVICE_UNAVAILABLE: 3000,
  SERVICE_ERROR: 3001,
  SERVICE_TIMEOUT: 3002,
  
  USER_NOT_FOUND: 4000,
  INVALID_INPUT: 4001,
  OPERATION_FAILED: 4002,
} as const;

export type ErrorCodeType = typeof ErrorCode[keyof typeof ErrorCode];

/**
 * 错误代码对应的默认消息
 */
export const ERROR_MESSAGES: Record<ErrorCodeType, string> = {
  [ErrorCode.OK]: 'Success',
  [ErrorCode.UNKNOWN_ERROR]: 'Unknown error',
  [ErrorCode.TIMEOUT]: 'Request timeout',
  [ErrorCode.INVALID_MESSAGE]: 'Invalid message format',
  
  [ErrorCode.UNAUTHORIZED]: 'Unauthorized',
  [ErrorCode.INVALID_TOKEN]: 'Invalid token',
  [ErrorCode.SESSION_EXPIRED]: 'Session expired',
  
  [ErrorCode.SERVICE_UNAVAILABLE]: 'Service unavailable',
  [ErrorCode.SERVICE_ERROR]: 'Service error',
  [ErrorCode.SERVICE_TIMEOUT]: 'Service timeout',
  
  [ErrorCode.USER_NOT_FOUND]: 'User not found',
  [ErrorCode.INVALID_INPUT]: 'Invalid input',
  [ErrorCode.OPERATION_FAILED]: 'Operation failed',
} as const;
