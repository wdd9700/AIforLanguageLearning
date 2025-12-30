/**
 * @fileoverview 软总线协议模块 (Softbus Protocol)
 * 
 * 基于 ZeroMQ 的 P2P 消息总线协议实现。
 * 负责消息帧的编码 (Encoding) 和解码 (Decoding)，以及协议版本控制。
 * 
 * 帧格式 (Frame Format):
 * ┌─────────────┬────────┬────────────┬─────────────────┐
 * │ HeaderLen   │ Header │ Encoding   │ Payload         │
 * ├─────────────┼────────┼────────────┼─────────────────┤
 * │ Varint      │ JSON   │ Varint     │ Uint8Array      │
 * └─────────────┴────────┴────────────┴─────────────────┘
 * 
 * 主要功能：
 * 1. Varint 编解码：实现 LEB128 变长整数编码，优化传输效率
 * 2. 消息序列化：将 Message 对象打包为二进制帧
 * 3. 消息反序列化：将二进制帧解析为 Message 对象
 * 4. 工具函数：ID 生成、版本验证、错误消息封装
 * 
 * 待改进项：
 * 1. 优化 Varint 实现以提高编解码性能
 * 2. 支持 Payload 压缩 (如 gzip, brotli) 以减少网络带宽占用
 * 3. 引入 Protocol Buffers 或 FlatBuffers 替代 JSON Header 以进一步提升性能
 * 4. 增加数据校验和 (Checksum) 机制
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { Message, MessageHeader, MessageType, PROTOCOL_VERSION, ErrorCode } from './types';

/**
 * Varint 编码
 * 将无符号整数编码为变长字节序列 (Uint8Array)
 * 参考: Protocol Buffers LEB128 标准
 * @param value 待编码的整数
 * @returns 编码后的字节数组
 */
export function encodeVarint(value: number): Uint8Array {
  const bytes: number[] = [];
  while (value > 0x7f) {
    bytes.push((value & 0x7f) | 0x80);
    value >>>= 7;
  }
  bytes.push(value & 0x7f);
  return new Uint8Array(bytes);
}

/**
 * Varint 解码
 * 从字节数组中解码出无符号整数
 * @param buffer 包含 Varint 的字节数组
 * @param offset 起始偏移量 (默认为 0)
 * @returns { value: 解码值, bytesRead: 读取的字节数 }
 */
export function decodeVarint(buffer: Uint8Array, offset = 0): { value: number; bytesRead: number } {
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
 * 消息编码
 * 将 Message 对象序列化为二进制帧
 * @param msg 消息对象
 * @returns 二进制帧数据 (Uint8Array)
 */
export function encodeMessage(msg: Message): Uint8Array {
  // 1. 序列化 header 为 JSON 字符串
  const headerJson = JSON.stringify(msg.header);
  const headerBytes = new TextEncoder().encode(headerJson);
  const headerLenVarint = encodeVarint(headerBytes.length);

  // 2. 编码 type 和 encoding 为 varint
  const typeVarint = encodeVarint(msg.type);
  const encodingVarint = encodeVarint(1); // 默认 encoding = 1 (utf-8 or binary)

  // 3. 计算总长度
  const totalLen =
    headerLenVarint.length +
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
 * 消息解码
 * 将二进制帧反序列化为 Message 对象
 * @param frame 二进制帧数据
 * @returns 解码后的消息对象和读取字节数，失败返回 null
 */
export function decodeMessage(frame: Uint8Array): { message: Message; bytesRead: number } | null {
  try {
    let offset = 0;

    // 1. 读取 header 长度
    const { value: headerLen, bytesRead: headerLenBytes } = decodeVarint(frame, offset);
    offset += headerLenBytes;

    // 2. 提取 header JSON
    const headerBytes = frame.slice(offset, offset + headerLen);
    offset += headerLen;

    const headerJson = new TextDecoder().decode(headerBytes);
    const header: MessageHeader = JSON.parse(headerJson);

    // 3. 读取 message type
    const { value: msgType, bytesRead: typeBytes } = decodeVarint(frame, offset);
    offset += typeBytes;

    // 4. 读取 encoding
    const { value: encoding, bytesRead: encodingBytes } = decodeVarint(frame, offset);
    offset += encodingBytes;

    // 5. 剩余部分为 payload
    const payload = frame.slice(offset);

    return {
      message: {
        header,
        type: msgType as MessageType,
        payload,
      },
      bytesRead: offset + payload.length,
    };
  } catch (e) {
    console.error('[softbus] 解码错误:', e);
    return null;
  }
}

/**
 * 验证消息版本
 * 确保消息版本与当前协议版本兼容
 */
export function validateMessageVersion(header: MessageHeader): boolean {
  return header.ver === PROTOCOL_VERSION;
}

/**
 * 生成唯一消息 ID
 * 格式: 时间戳(36进制)-随机数(36进制)
 */
export function generateMsgId(): string {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).substring(2, 8);
  return `${ts}-${rand}`;
}

/**
 * 生成追踪 ID (Trace ID)
 * 用于全链路追踪
 */
export function generateTraceId(): string {
  return generateMsgId();
}

/**
 * 创建错误消息 Payload
 * @param code 错误代码
 * @param message 错误描述
 * @param details 详细信息 (可选)
 * @returns 序列化后的错误 Payload
 */
export function createErrorMessage(
  code: ErrorCode,
  message: string,
  details?: Record<string, any>
): Uint8Array {
  const errorPayload = {
    code,
    message,
    details,
  };
  return new TextEncoder().encode(JSON.stringify(errorPayload));
}

/**
 * 解析错误消息 Payload
 * @param payload 错误消息 Payload
 * @returns 解析后的错误对象
 */
export function parseErrorMessage(payload: Uint8Array): { code: ErrorCode; message: string; details?: any } {
  try {
    const json = new TextDecoder().decode(payload);
    return JSON.parse(json);
  } catch {
    return {
      code: ErrorCode.UNKNOWN,
      message: 'Failed to parse error message',
    };
  }
}
