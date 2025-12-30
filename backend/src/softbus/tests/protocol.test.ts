/**
 * Softbus Protocol Tests
 * 测试帧编码/解码、varint 序列化等
 */

import { encodeVarint, decodeVarint, encodeMessage, decodeMessage, generateMsgId, generateTraceId } from '../protocol';
import { Message, MessageHeader, MessageType, PROTOCOL_VERSION } from '../types';

describe('Protocol Encoding/Decoding', () => {
  it('should encode/decode varint correctly', () => {
    const testCases = [
      0, 1, 127, 128, 255, 256, 16383, 16384, 0x7fffffff
    ];

    for (const value of testCases) {
      const encoded = encodeVarint(value);
      const { value: decoded } = decodeVarint(encoded);
      expect(decoded).toBe(value);
    }
  });

  it('should encode/decode message frame correctly', () => {
    const header: MessageHeader = {
      ver: PROTOCOL_VERSION,
      msgId: generateMsgId(),
      seq: 0,
      ts: Date.now(),
      traceId: generateTraceId(),
      contentType: 'application/json',
      encoding: 'utf-8',
      meta: { test: 'value' },
    };

    const payload = new TextEncoder().encode('hello softbus');

    const msg: Message = {
      header,
      type: MessageType.PUB,
      payload,
    };

    const frame = encodeMessage(msg);
    const result = decodeMessage(frame);

    expect(result).not.toBeNull();
    if (result) {
      expect(result.message.header.msgId).toBe(header.msgId);
      expect(result.message.type).toBe(MessageType.PUB);
      expect(new TextDecoder().decode(result.message.payload)).toBe('hello softbus');
    }
  });

  it('should handle binary payload correctly', () => {
    const payload = new Uint8Array([0xff, 0xfe, 0xfd, 0xfc, 0xfb]);

    const msg: Message = {
      header: {
        ver: PROTOCOL_VERSION,
        msgId: generateMsgId(),
        seq: 1,
        ts: Date.now(),
        traceId: generateTraceId(),
        contentType: 'application/octet-stream',
        encoding: 'binary',
      },
      type: MessageType.CHUNK_PUT,
      payload,
    };

    const frame = encodeMessage(msg);
    const result = decodeMessage(frame);

    expect(result).not.toBeNull();
    if (result) {
      expect(result.message.payload).toEqual(payload);
    }
  });
});

describe('Message ID Generation', () => {
  it('should generate unique message IDs', () => {
    const ids = new Set<string>();
    for (let i = 0; i < 1000; i++) {
      ids.add(generateMsgId());
    }
    expect(ids.size).toBe(1000); // 所有 ID 应该唯一
  });

  it('should generate unique trace IDs', () => {
    const ids = new Set<string>();
    for (let i = 0; i < 1000; i++) {
      ids.add(generateTraceId());
    }
    expect(ids.size).toBe(1000); // 所有 ID 应该唯一
  });
});
