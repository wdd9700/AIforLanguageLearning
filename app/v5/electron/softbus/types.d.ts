/**
 * Softbus - ZeroMQ-based P2P Message Bus for MMLS
 * Type Definitions
 */
/**
 * 协议版本
 */
export declare const PROTOCOL_VERSION = 1;
/**
 * 消息头结构
 */
export interface MessageHeader {
    /** 协议版本 */
    ver: number;
    /** 全局唯一消息 ID */
    msgId: string;
    /** 序列号（流式消息） */
    seq: number;
    /** 时间戳（毫秒） */
    ts: number;
    /** 链路追踪 ID */
    traceId: string;
    /** 内容类型 */
    contentType: string;
    /** 编码方式 */
    encoding: string;
    /** 自定义元数据 */
    meta?: Record<string, any>;
}
/**
 * 消息类型枚举
 */
export declare enum MessageType {
    /** 广播/发布 */
    PUB = 1,
    /** RPC 请求 */
    RPC_REQ = 2,
    /** RPC 响应 */
    RPC_RES = 3,
    /** 流打开 */
    STREAM_OPEN = 16,
    /** 流数据 */
    STREAM_DATA = 17,
    /** 流结束 */
    STREAM_END = 18,
    /** 块存储 */
    CHUNK_PUT = 32,
    /** 块检索 */
    CHUNK_GET = 33,
    /** 心跳/存活检测 */
    HEARTBEAT = 48,
    /** 错误响应 */
    ERROR = 255
}
/**
 * 完整消息结构
 */
export interface Message {
    header: MessageHeader;
    type: MessageType;
    payload: Uint8Array;
}
/**
 * 错误码
 */
export declare enum ErrorCode {
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
    /** 超时 */
    TIMEOUT = 5,
    /** 连接中断 */
    CONNECTION_LOST = 6,
    /** 服务不可用 */
    SERVICE_UNAVAILABLE = 7,
    /** 未知错误 */
    UNKNOWN = 999
}
/**
 * 错误消息
 */
export interface ErrorMessage {
    code: ErrorCode;
    message: string;
    details?: Record<string, any>;
}
/**
 * PeerID（身份标识）
 */
export interface PeerId {
    /** 公钥（base58 编码） */
    publicKey: string;
    /** 派生 ID */
    id: string;
}
/**
 * 服务注册信息
 */
export interface ServiceInfo {
    /** 服务名称 */
    name: string;
    /** 服务类型 */
    type: string;
    /** 服务端口 */
    port: number;
    /** 所属 PeerID */
    peerId: string;
    /** 心跳时间戳 */
    heartbeatAt: number;
    /** 自定义属性 */
    attributes?: Record<string, string>;
}
/**
 * 连接选项
 */
export interface ConnectOptions {
    /** ZMQ 端点 */
    endpoint: string;
    /** 预共享密钥（PSK）用于加密 */
    psk?: string;
    /** 客户端证书（公钥） */
    clientCert?: string;
    /** 连接超时（毫秒） */
    connectTimeout?: number;
    /** 心跳间隔（毫秒） */
    heartbeatInterval?: number;
    /** 重连策略 */
    reconnectPolicy?: {
        maxRetries: number;
        initialDelayMs: number;
        maxDelayMs: number;
        backoffMultiplier: number;
    };
}
/**
 * Pub/Sub 选项
 */
export interface PubSubOptions {
    /** 主题 */
    topic: string;
    /** 订阅者回调 */
    onMessage?: (msg: Message) => void;
    /** 错误回调 */
    onError?: (err: ErrorMessage) => void;
}
/**
 * RPC 请求选项
 */
export interface RpcRequestOptions {
    /** 方法名称 */
    method: string;
    /** 请求参数（JSON 或二进制） */
    params?: any;
    /** 请求超时（毫秒） */
    timeout?: number;
}
/**
 * RPC 响应
 */
export interface RpcResponse {
    /** 是否成功 */
    success: boolean;
    /** 结果或错误 */
    data?: any;
    error?: ErrorMessage;
}
/**
 * 双向流选项
 */
export interface StreamOptions {
    /** 流 ID */
    streamId: string;
    /** 数据到达回调 */
    onData?: (payload: Uint8Array) => void;
    /** 流关闭回调 */
    onClose?: (reason?: string) => void;
    /** 错误回调 */
    onError?: (err: ErrorMessage) => void;
    /** 背压水位（字节） */
    backpressureLimit?: number;
}
/**
 * 块存储选项
 */
export interface ChunkOptions {
    /** 对象 ID */
    objectId: string;
    /** 块编号 */
    chunkNo: number;
    /** 总块数 */
    totalChunks: number;
    /** 块大小（字节） */
    chunkSize: number;
    /** 校验和（可选） */
    checksum?: string;
}
/**
 * 客户端/服务端事件
 */
export interface BusEvent {
    type: 'connected' | 'disconnected' | 'reconnecting' | 'error' | 'heartbeat';
    payload?: any;
    timestamp: number;
}
/**
 * 发现事件
 */
export interface DiscoveryEvent {
    type: 'service-found' | 'service-lost';
    service: ServiceInfo;
    timestamp: number;
}
//# sourceMappingURL=types.d.ts.map