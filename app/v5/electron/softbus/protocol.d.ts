/**
 * Softbus - ZeroMQ-based P2P Message Bus
 * Protocol: Frame Encoding/Decoding
 *
 * Frame Format:
 * ┌─────────────┬────────┬────────────┬─────────────────┐
 * │ HeaderLen   │ Header │ Encoding   │ Payload         │
 * ├─────────────┼────────┼────────────┼─────────────────┤
 * │ Varint      │ JSON   │ Varint     │ Uint8Array      │
 * └─────────────┴────────┴────────────┴─────────────────┘
 *
 * Varint: 变长整数编码（LEB128）
 */
import { Message, MessageHeader, ErrorCode } from './types.js';
/**
 * Varint 编码：无符号整数 → Uint8Array
 * 参考：Protocol Buffers LEB128
 */
export declare function encodeVarint(value: number): Uint8Array;
/**
 * Varint 解码：Uint8Array → { value, bytesRead }
 */
export declare function decodeVarint(buffer: Uint8Array, offset?: number): {
    value: number;
    bytesRead: number;
};
/**
 * 将消息编码为帧（字节数组）
 */
export declare function encodeMessage(msg: Message): Uint8Array;
/**
 * 将帧解码为消息
 */
export declare function decodeMessage(frame: Uint8Array): {
    message: Message;
    bytesRead: number;
} | null;
/**
 * 验证消息版本
 */
export declare function validateMessageVersion(header: MessageHeader): boolean;
/**
 * 生成唯一消息 ID（基于时间戳 + 随机数）
 */
export declare function generateMsgId(): string;
/**
 * 生成追踪 ID
 */
export declare function generateTraceId(): string;
/**
 * 创建错误消息
 */
export declare function createErrorMessage(code: ErrorCode, message: string, details?: Record<string, any>): Uint8Array;
/**
 * 解析错误消息
 */
export declare function parseErrorMessage(payload: Uint8Array): {
    code: ErrorCode;
    message: string;
    details?: any;
};
//# sourceMappingURL=protocol.d.ts.map