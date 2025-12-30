/**
 * Softbus - ZeroMQ-based P2P Message Bus for MMLS
 * Type Definitions
 */
/**
 * 协议版本
 */
export const PROTOCOL_VERSION = 1;
/**
 * 消息类型枚举
 */
export var MessageType;
(function (MessageType) {
    /** 广播/发布 */
    MessageType[MessageType["PUB"] = 1] = "PUB";
    /** RPC 请求 */
    MessageType[MessageType["RPC_REQ"] = 2] = "RPC_REQ";
    /** RPC 响应 */
    MessageType[MessageType["RPC_RES"] = 3] = "RPC_RES";
    /** 流打开 */
    MessageType[MessageType["STREAM_OPEN"] = 16] = "STREAM_OPEN";
    /** 流数据 */
    MessageType[MessageType["STREAM_DATA"] = 17] = "STREAM_DATA";
    /** 流结束 */
    MessageType[MessageType["STREAM_END"] = 18] = "STREAM_END";
    /** 块存储 */
    MessageType[MessageType["CHUNK_PUT"] = 32] = "CHUNK_PUT";
    /** 块检索 */
    MessageType[MessageType["CHUNK_GET"] = 33] = "CHUNK_GET";
    /** 心跳/存活检测 */
    MessageType[MessageType["HEARTBEAT"] = 48] = "HEARTBEAT";
    /** 错误响应 */
    MessageType[MessageType["ERROR"] = 255] = "ERROR";
})(MessageType || (MessageType = {}));
/**
 * 错误码
 */
export var ErrorCode;
(function (ErrorCode) {
    /** 成功 */
    ErrorCode[ErrorCode["OK"] = 0] = "OK";
    /** 协议版本不兼容 */
    ErrorCode[ErrorCode["INVALID_VERSION"] = 1] = "INVALID_VERSION";
    /** 解码错误 */
    ErrorCode[ErrorCode["DECODE_ERROR"] = 2] = "DECODE_ERROR";
    /** 加密验证失败 */
    ErrorCode[ErrorCode["CRYPTO_FAILED"] = 3] = "CRYPTO_FAILED";
    /** 身份认证失败 */
    ErrorCode[ErrorCode["AUTH_FAILED"] = 4] = "AUTH_FAILED";
    /** 超时 */
    ErrorCode[ErrorCode["TIMEOUT"] = 5] = "TIMEOUT";
    /** 连接中断 */
    ErrorCode[ErrorCode["CONNECTION_LOST"] = 6] = "CONNECTION_LOST";
    /** 服务不可用 */
    ErrorCode[ErrorCode["SERVICE_UNAVAILABLE"] = 7] = "SERVICE_UNAVAILABLE";
    /** 未知错误 */
    ErrorCode[ErrorCode["UNKNOWN"] = 999] = "UNKNOWN";
})(ErrorCode || (ErrorCode = {}));
//# sourceMappingURL=types.js.map