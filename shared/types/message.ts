/**
 * 软总线消息协议
 * 前后端共用定义
 */

export type MessageType = 'request' | 'response' | 'stream' | 'pubsub' | 'error';
export type PayloadType = 'text' | 'image' | 'audio' | 'binary' | 'json';
export type Encoding = 'utf8' | 'base64' | 'binary';

/**
 * 消息有效负载
 */
export interface Payload {
  data: any;
  type: PayloadType;
  encoding: Encoding;
  size: number;
  chunkIndex?: number;       // 分片索引
  totalChunks?: number;      // 总分片数
}

/**
 * 消息元数据
 */
export interface MessageMetadata {
  timestamp: number;
  userId?: string;           // 认证用户 ID
  requestId: string;         // 请求 ID（追踪）
  timeout: number;           // 超时时间 (ms)
  retries?: number;
}

/**
 * 统一消息格式
 */
export interface Message {
  id: string;                // 消息 ID (UUID)
  sessionId: string;         // 会话 ID
  peerId: string;            // 发送方 PeerID
  topic: string;             // 主题 (svc/*, res/*, learn/*)
  type: MessageType;
  payload: Payload;
  metadata: MessageMetadata;
  signature?: string;        // Ed25519 签名
}

/**
 * 响应消息
 */
export interface ResponseMessage extends Message {
  type: 'response';
  status: 'success' | 'error';
  code: number;
  message?: string;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}

/**
 * 流消息（用于长连接）
 */
export interface StreamMessage extends Message {
  type: 'stream';
  isEnd?: boolean;           // 是否流结束
}

/**
 * 发布/订阅消息
 */
export interface PubSubMessage extends Message {
  type: 'pubsub';
  subscribers?: number;      // 订阅者数
}

/**
 * 消息主题常量
 */
export const TOPICS = {
  // 服务请求
  SERVICE: {
    OCR: 'svc/ocr',
    ASR: 'svc/asr',
    TTS: 'svc/tts',
    LLM: 'svc/llm',
  },
  
  // 管道
  PIPELINE: {
    OCR_TO_LLM: 'svc/ocr-to-llm',
    ASR_TO_LLM: 'svc/asr-to-llm',
  },
  
  // 学情相关
  LEARNING: {
    RECORD: 'learning/record',
    PROFILE: 'learning/profile',
    ANALYSIS: 'learning/analysis',
  },
  
  // 认证
  AUTH: {
    LOGIN: 'auth/login',
    LOGOUT: 'auth/logout',
    REFRESH: 'auth/refresh',
  },
  
  // 系统
  SYSTEM: {
    HEARTBEAT: 'system/heartbeat',
    DISCOVER: 'system/discover',
    STATUS: 'system/status',
  },
};

/**
 * 错误代码
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
 * 错误消息映射
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
