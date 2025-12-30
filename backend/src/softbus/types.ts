/**
 * @fileoverview 软总线类型定义模块 (Softbus Types)
 * 
 * 定义了 MMLS 系统中基于 ZeroMQ 的 P2P 消息总线的所有核心数据结构。
 * 涵盖了协议版本、消息头、消息类型、错误码、服务信息以及各类操作的配置选项。
 * 
 * 主要内容：
 * 1. 协议基础：PROTOCOL_VERSION, MessageHeader, MessageType, Message
 * 2. 错误处理：ErrorCode, ErrorMessage
 * 3. 身份与服务：PeerId, ServiceInfo
 * 4. 操作配置：ConnectOptions, PubSubOptions, RpcRequestOptions, StreamOptions
 * 5. 事件定义：BusEvent, DiscoveryEvent
 * 
 * 待改进项：
 * 1. 细化错误码定义，区分网络错误、协议错误和业务错误
 * 2. 完善类型定义，增加更多严格的类型检查
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

/**
 * 协议版本号
 * 用于兼容性检查
 */
export const PROTOCOL_VERSION = 1;

/**
 * 消息头结构
 * 包含消息的元数据，用于路由、追踪和解析
 */
export interface MessageHeader {
  /** 协议版本 */
  ver: number;
  /** 全局唯一消息 ID (UUID) */
  msgId: string;
  /** 序列号 (用于流式消息排序) */
  seq: number;
  /** 发送时间戳 (毫秒) */
  ts: number;
  /** 链路追踪 ID (Trace ID) */
  traceId: string;
  /** 内容类型 (MIME Type, 如 "application/json") */
  contentType: string;
  /** 编码方式 (如 "utf-8", "gzip") */
  encoding: string;
  /** 自定义元数据 (键值对) */
  meta?: Record<string, any>;
}

/**
 * 消息类型枚举
 * 定义了总线支持的所有消息交互模式
 */
export enum MessageType {
  /** 广播/发布 (Pub/Sub) */
  PUB = 0x01,
  /** RPC 请求 (Request) */
  RPC_REQ = 0x02,
  /** RPC 响应 (Response) */
  RPC_RES = 0x03,
  /** 流打开 (Stream Open) */
  STREAM_OPEN = 0x10,
  /** 流数据 (Stream Data) */
  STREAM_DATA = 0x11,
  /** 流结束 (Stream End) */
  STREAM_END = 0x12,
  /** 块存储写入 (Chunk Put) */
  CHUNK_PUT = 0x20,
  /** 块存储读取 (Chunk Get) */
  CHUNK_GET = 0x21,
  /** 心跳/存活检测 (Heartbeat) */
  HEARTBEAT = 0x30,
  /** 错误响应 (Error) */
  ERROR = 0xff,
}

/**
 * 完整消息结构
 * 包含头部、类型和负载
 */
export interface Message {
  header: MessageHeader;
  type: MessageType;
  payload: Uint8Array;
}

/**
 * 系统错误码枚举
 */
export enum ErrorCode {
  /** 成功 */
  OK = 0,
  /** 协议版本不兼容 */
  INVALID_VERSION = 1,
  /** 解码错误 */
  DECODE_ERROR = 2,
  /** 加密验证失败 */
  CRYPTO_FAILED = 3,
  /** 身份认证失败 */
  AUTH_FAILED = 4,
  /** 操作超时 */
  TIMEOUT = 5,
  /** 连接中断 */
  CONNECTION_LOST = 6,
  /** 服务不可用 */
  SERVICE_UNAVAILABLE = 7,
  /** 未知错误 */
  UNKNOWN = 999,
}

/**
 * 错误消息结构
 */
export interface ErrorMessage {
  code: ErrorCode;
  message: string;
  details?: Record<string, any>;
}

/**
 * PeerID (节点身份标识)
 */
export interface PeerId {
  /** 公钥 (Base58 编码) */
  publicKey: string;
  /** 派生 ID (公钥哈希) */
  id: string;
}

/**
 * 服务注册信息
 * 用于服务发现
 */
export interface ServiceInfo {
  /** 服务名称 */
  name: string;
  /** 服务类型 */
  type: string;
  /** 服务端口 */
  port: number;
  /** 所属节点 ID */
  peerId: string;
  /** 最后心跳时间戳 */
  heartbeatAt: number;
  /** 自定义属性 */
  attributes?: Record<string, string>;
}

/**
 * 连接配置选项
 */
export interface ConnectOptions {
  /** ZMQ 端点地址 (如 tcp://127.0.0.1:5555) */
  endpoint: string;
  /** 预共享密钥 (PSK) 用于加密通信 */
  psk?: string;
  /** 客户端证书 (公钥) */
  clientCert?: string;
  /** 连接超时时间 (毫秒) */
  connectTimeout?: number;
  /** 心跳间隔 (毫秒) */
  heartbeatInterval?: number;
  /** 重连策略配置 */
  reconnectPolicy?: {
    maxRetries: number;       // 最大重试次数
    initialDelayMs: number;   // 初始延迟
    maxDelayMs: number;       // 最大延迟
    backoffMultiplier: number;// 退避倍数
  };
}

/**
 * 发布/订阅配置选项
 */
export interface PubSubOptions {
  /** 订阅主题 */
  topic: string;
  /** 消息回调函数 */
  onMessage?: (msg: Message) => void;
  /** 错误回调函数 */
  onError?: (err: ErrorMessage) => void;
}

/**
 * RPC 请求配置选项
 */
export interface RpcRequestOptions {
  /** 调用的方法名称 */
  method: string;
  /** 请求参数 (JSON 对象或二进制数据) */
  params?: any;
  /** 请求超时时间 (毫秒) */
  timeout?: number;
}

/**
 * RPC 响应结构
 */
export interface RpcResponse {
  /** 调用是否成功 */
  success: boolean;
  /** 成功时的返回数据 */
  data?: any;
  /** 失败时的错误信息 */
  error?: ErrorMessage;
}

/**
 * 双向流配置选项
 */
export interface StreamOptions {
  /** 流 ID */
  streamId: string;
  /** 数据接收回调 */
  onData?: (payload: Uint8Array) => void;
  /** 流关闭回调 */
  onClose?: (reason?: string) => void;
  /** 错误回调 */
  onError?: (err: ErrorMessage) => void;
  /** 背压水位限制 (字节) */
  backpressureLimit?: number;
}

/**
 * 块存储操作选项
 */
export interface ChunkOptions {
  /** 对象 ID */
  objectId: string;
  /** 当前块编号 */
  chunkNo: number;
  /** 总块数 */
  totalChunks: number;
  /** 块大小 (字节) */
  chunkSize: number;
  /** 数据校验和 (可选) */
  checksum?: string;
}

/**
 * 总线事件
 * 描述连接状态变化
 */
export interface BusEvent {
  type: 'connected' | 'disconnected' | 'reconnecting' | 'error' | 'heartbeat';
  payload?: any;
  timestamp: number;
}

/**
 * 服务发现事件
 */
export interface DiscoveryEvent {
  type: 'service-found' | 'service-lost';
  service: ServiceInfo;
  timestamp: number;
}
