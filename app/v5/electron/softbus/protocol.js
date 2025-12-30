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
import { PROTOCOL_VERSION, ErrorCode } from './types.js';
/**
 * Varint 编码：无符号整数 → Uint8Array
 * 参考：Protocol Buffers LEB128
 */
export function encodeVarint(value) {
    const bytes = [];
    while (value > 0x7f) {
        bytes.push((value & 0x7f) | 0x80);
        value >>>= 7;
    }
    bytes.push(value & 0x7f);
    return new Uint8Array(bytes);
}
/**
 * Varint 解码：Uint8Array → { value, bytesRead }
 */
export function decodeVarint(buffer, offset = 0) {
    let value = 0;
    let shift = 0;
    let bytesRead = 0;
    for (let i = offset; i < buffer.length; i++) {
        const byte = buffer[i];
        value |= (byte & 0x7f) << shift;
        bytesRead++;
        if ((byte & 0x80) === 0) {
            break;
        }
        shift += 7;
    }
    return { value, bytesRead };
}
/**
 * 将消息编码为帧（字节数组）
 */
export function encodeMessage(msg) {
    // 1. 序列化 header 为 JSON
    const headerJson = JSON.stringify(msg.header);
    const headerBytes = new TextEncoder().encode(headerJson);
    const headerLenVarint = encodeVarint(headerBytes.length);
    // 2. 编码 type 和 encoding 为 varint
    const typeVarint = encodeVarint(msg.type);
    const encodingVarint = encodeVarint(1); // 默认 encoding = 1（utf-8 or binary）
    // 3. 计算总长度
    const totalLen = headerLenVarint.length +
        headerBytes.length +
        typeVarint.length +
        encodingVarint.length +
        msg.payload.length;
    // 4. 拼接成完整帧
    const frame = new Uint8Array(totalLen);
    let offset = 0;
    frame.set(headerLenVarint, offset);
    offset += headerLenVarint.length;
    frame.set(headerBytes, offset);
    offset += headerBytes.length;
    frame.set(typeVarint, offset);
    offset += typeVarint.length;
    frame.set(encodingVarint, offset);
    offset += encodingVarint.length;
    frame.set(msg.payload, offset);
    return frame;
}
/**
 * 将帧解码为消息
 */
export function decodeMessage(frame) {
    try {
        let offset = 0;
        // 1. 读取 header 长度
        const { value: headerLen, bytesRead: headerLenBytes } = decodeVarint(frame, offset);
        offset += headerLenBytes;
        // 2. 提取 header JSON
        const headerBytes = frame.slice(offset, offset + headerLen);
        offset += headerLen;
        const headerJson = new TextDecoder().decode(headerBytes);
        const header = JSON.parse(headerJson);
        // 3. 读取 message type
        const { value: msgType, bytesRead: typeBytes } = decodeVarint(frame, offset);
        offset += typeBytes;
        // 4. 读取 encoding
        const { value: encoding, bytesRead: encodingBytes } = decodeVarint(frame, offset);
        offset += encodingBytes;
        // 5. 剩余为 payload
        const payload = frame.slice(offset);
        return {
            message: {
                header,
                type: msgType,
                payload,
            },
            bytesRead: offset + payload.length,
        };
    }
    catch (e) {
        console.error('[softbus] decode error:', e);
        return null;
    }
}
/**
 * 验证消息版本
 */
export function validateMessageVersion(header) {
    return header.ver === PROTOCOL_VERSION;
}
/**
 * 生成唯一消息 ID（基于时间戳 + 随机数）
 */
export function generateMsgId() {
    const ts = Date.now().toString(36);
    const rand = Math.random().toString(36).substring(2, 8);
    return `${ts}-${rand}`;
}
/**
 * 生成追踪 ID
 */
export function generateTraceId() {
    return generateMsgId();
}
/**
 * 创建错误消息
 */
export function createErrorMessage(code, message, details) {
    const errorPayload = {
        code,
        message,
        details,
    };
    return new TextEncoder().encode(JSON.stringify(errorPayload));
}
/**
 * 解析错误消息
 */
export function parseErrorMessage(payload) {
    try {
        const json = new TextDecoder().decode(payload);
        return JSON.parse(json);
    }
    catch {
        return {
            code: ErrorCode.UNKNOWN,
            message: 'Failed to parse error message',
        };
    }
}
//# sourceMappingURL=protocol.js.map