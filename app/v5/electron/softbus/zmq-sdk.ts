/**
 * @fileoverview 软总线客户端 SDK (Softbus Client SDK)
 * @description
 * 该模块基于 ZeroMQ 实现了软总线的客户端功能，支持发布/订阅、RPC 和流式传输。
 * 
 * 主要功能包括：
 * 1. 连接管理 (Connection Management)：
 *    - 连接/断开 ZeroMQ 端点 (connect, disconnect)
 *    - 心跳维持 (startHeartbeat)
 *    - 自动重连 (TODO)
 * 
 * 2. 消息通信 (Messaging)：
 *    - 发布消息 (publish)
 *    - 订阅主题 (subscribe, unsubscribe)
 *    - RPC 调用 (rpc)
 * 
 * 3. 流式传输 (Streaming)：
 *    - 打开双向流 (openStream)
 *    - 发送流数据 (Stream.send)
 *    - 关闭流 (Stream.end)
 * 
 * 4. 安全性 (Security)：
 *    - 消息加密/解密 (encryptFrame, decryptFrame)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import zmq from 'zeromq';
import { Message, MessageType, ConnectOptions, PubSubOptions, RpcRequestOptions, StreamOptions, ErrorCode, BusEvent, ErrorMessage, RpcResponse } from './types.js';
import { encodeMessage, decodeMessage, generateMsgId, generateTraceId, createErrorMessage, parseErrorMessage } from './protocol.js';
import { encrypt, decrypt, EncryptedData } from './crypto.js';

/**
 * Softbus Client (ZMQ 包装器)
 */
export class SoftbusClient {
  private endpoint: string;
  private psk?: string;
  private sock?: any; // zmq.Socket (native module, no type definitions)
  private subscribers: Map<string, (msg: Message) => void> = new Map();
  private rpcCallbacks: Map<string, (res: any) => void> = new Map();
  private streams: Map<string, StreamHandler> = new Map();
  private eventHandlers: ((event: BusEvent) => void)[] = [];
  private heartbeatTimer?: NodeJS.Timeout;
  private reconnectTimer?: NodeJS.Timeout;
  private isConnected = false;

  constructor(options: ConnectOptions) {
    this.endpoint = options.endpoint;
    this.psk = options.psk;
  }

  /**
   * 连接到软总线
   */
  async connect(): Promise<void> {
    try {
      this.sock = new zmq.Dealer({ linger: 0 });
      
      // 如果配置了 PSK，则设置加密前缀
      if (this.psk) {
        // ZMQ 的 CURVE 加密需要特殊设置（这里简化处理）
        // 实际应用中需要调用 sock.curveSecretKey() 等 API
      }

      await this.sock.connect(this.endpoint);
      this.isConnected = true;
      this.emit({ type: 'connected', timestamp: Date.now() });

      // 启动消息接收循环
      this.startReceiving();

      // 启动心跳
      this.startHeartbeat();
    } catch (err) {
      console.error('[softbus] connect error:', err);
      this.emit({ type: 'error', payload: err, timestamp: Date.now() });
      throw err;
    }
  }

  /**
   * 断开连接
   */
  async disconnect(): Promise<void> {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    if (this.reconnectTimer) clearInterval(this.reconnectTimer);

    if (this.sock) {
      await this.sock.close();
      this.sock = undefined;
    }

    this.isConnected = false;
    this.emit({ type: 'disconnected', timestamp: Date.now() });
  }

  /**
   * 发布消息
   */
  async publish(topic: string, payload: Uint8Array, contentType: string = 'application/octet-stream'): Promise<void> {
    if (!this.sock || !this.isConnected) {
      throw new Error('Not connected');
    }

    const msg: Message = {
      header: {
        ver: 1,
        msgId: generateMsgId(),
        seq: 0,
        ts: Date.now(),
        traceId: generateTraceId(),
        contentType,
        encoding: 'binary',
        meta: { topic },
      },
      type: MessageType.PUB,
      payload,
    };

    const frame = encodeMessage(msg);
    const encrypted = this.psk ? this.encryptFrame(frame) : frame;

    // ZMQ DEALER 发送多帧
    await this.sock.send([topic, encrypted]);
  }

  /**
   * 订阅主题
   */
  subscribe(options: PubSubOptions): void {
    const { topic, onMessage, onError } = options;
    this.subscribers.set(topic, onMessage || (() => {}));
  }

  /**
   * 取消订阅
   */
  unsubscribe(topic: string): void {
    this.subscribers.delete(topic);
  }

  /**
   * 发送 RPC 请求
   */
  async rpc(options: RpcRequestOptions): Promise<RpcResponse> {
    if (!this.sock || !this.isConnected) {
      throw new Error('Not connected');
    }

    const msgId = generateMsgId();
    const payload = new TextEncoder().encode(JSON.stringify(options.params || {}));

    const msg: Message = {
      header: {
        ver: 1,
        msgId,
        seq: 0,
        ts: Date.now(),
        traceId: generateTraceId(),
        contentType: 'application/json',
        encoding: 'utf-8',
        meta: { method: options.method },
      },
      type: MessageType.RPC_REQ,
      payload,
    };

    const frame = encodeMessage(msg);
    const encrypted = this.psk ? this.encryptFrame(frame) : frame;

    // 发送请求
    await this.sock.send([options.method, encrypted]);

    // 等待响应（这里简化处理，实际应用中应该有超时与重试）
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error('RPC timeout'));
      }, options.timeout || 5000);

      this.rpcCallbacks.set(msgId, (res) => {
        clearTimeout(timeoutId);
        resolve(res);
      });
    });
  }

  /**
   * 打开双向流
   */
  openStream(options: StreamOptions): Stream {
    const stream = new Stream(options.streamId, this.sock!, this.psk);
    this.streams.set(options.streamId, { handler: options, stream });
    return stream;
  }

  /**
   * 注册事件监听器
   */
  on(handler: (event: BusEvent) => void): void {
    this.eventHandlers.push(handler);
  }

  /**
   * 发出事件
   */
  private emit(event: BusEvent): void {
    for (const handler of this.eventHandlers) {
      try {
        handler(event);
      } catch (err) {
        console.error('[softbus] event handler error:', err);
      }
    }
  }

  /**
   * 启动消息接收循环
   */
  private async startReceiving(): Promise<void> {
    if (!this.sock) return;

    try {
      for await (const [topic, frame] of this.sock) {
        try {
          // 解密（如果需要）
          const decrypted = this.psk ? this.decryptFrame(frame as Uint8Array) : (frame as Uint8Array);
          if (!decrypted) continue;

          // 解码消息
          const result = decodeMessage(decrypted);
          if (!result) continue;

          const { message } = result;

          // 根据消息类型分发
          switch (message.type) {
            case MessageType.PUB: {
              const handler = this.subscribers.get(topic as string);
              if (handler) handler(message);
              break;
            }
            case MessageType.RPC_RES: {
              const callback = this.rpcCallbacks.get(message.header.msgId);
              if (callback) {
                const res = JSON.parse(new TextDecoder().decode(message.payload));
                callback(res);
                this.rpcCallbacks.delete(message.header.msgId);
              }
              break;
            }
            case MessageType.STREAM_DATA: {
              const streamHandler = this.streams.get(message.header.meta?.streamId);
              if (streamHandler?.handler.onData) {
                streamHandler.handler.onData(message.payload);
              }
              break;
            }
            case MessageType.ERROR: {
              const error = parseErrorMessage(message.payload);
              this.emit({ type: 'error', payload: error, timestamp: Date.now() });
              break;
            }
          }
        } catch (err) {
          console.error('[softbus] message processing error:', err);
        }
      }
    } catch (err) {
      console.error('[softbus] receiving error:', err);
      this.isConnected = false;
      this.emit({ type: 'disconnected', timestamp: Date.now() });
    }
  }

  /**
   * 启动心跳
   */
  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(async () => {
      if (!this.sock || !this.isConnected) return;

      try {
        const msg: Message = {
          header: {
            ver: 1,
            msgId: generateMsgId(),
            seq: 0,
            ts: Date.now(),
            traceId: generateTraceId(),
            contentType: 'application/json',
            encoding: 'utf-8',
          },
          type: MessageType.HEARTBEAT,
          payload: new Uint8Array(0),
        };

        const frame = encodeMessage(msg);
        const encrypted = this.psk ? this.encryptFrame(frame) : frame;
        await this.sock.send(['__heartbeat__', encrypted]);

        this.emit({ type: 'heartbeat', timestamp: Date.now() });
      } catch (err) {
        console.error('[softbus] heartbeat error:', err);
      }
    }, 30000); // 30 秒一次
  }

  /**
   * 加密帧
   */
  private encryptFrame(frame: Uint8Array): Uint8Array {
    if (!this.psk) return frame;

    const encrypted = encrypt(frame, this.psk);
    const result = new Uint8Array(encrypted.iv.length + encrypted.authTag.length + encrypted.ciphertext.length + 4);
    let offset = 0;

    // 存储 IV 长度
    result[offset] = encrypted.iv.length;
    offset += 1;

    // 存储 IV
    result.set(encrypted.iv, offset);
    offset += encrypted.iv.length;

    // 存储 AuthTag 长度
    result[offset] = encrypted.authTag.length;
    offset += 1;

    // 存储 AuthTag
    result.set(encrypted.authTag, offset);
    offset += encrypted.authTag.length;

    // 存储密文
    result.set(encrypted.ciphertext, offset);

    return result;
  }

  /**
   * 解密帧
   */
  private decryptFrame(frame: Uint8Array): Uint8Array | null {
    if (!this.psk) return frame;

    try {
      let offset = 0;

      // 读取 IV
      const ivLen = frame[offset];
      offset += 1;
      const iv = frame.slice(offset, offset + ivLen);
      offset += ivLen;

      // 读取 AuthTag
      const authTagLen = frame[offset];
      offset += 1;
      const authTag = frame.slice(offset, offset + authTagLen);
      offset += authTagLen;

      // 读取密文
      const ciphertext = frame.slice(offset);

      return decrypt({ ciphertext, iv, authTag }, this.psk);
    } catch (err) {
      console.error('[softbus] decrypt error:', err);
      return null;
    }
  }
}

/**
 * 双向流处理器
 */
class Stream {
  constructor(
    private streamId: string,
    private sock: any, // zmq.Socket (native module, no type definitions)
    private psk?: string
  ) {}

  async send(payload: Uint8Array): Promise<void> {
    const msg: Message = {
      header: {
        ver: 1,
        msgId: generateMsgId(),
        seq: 0,
        ts: Date.now(),
        traceId: generateTraceId(),
        contentType: 'application/octet-stream',
        encoding: 'binary',
        meta: { streamId: this.streamId },
      },
      type: MessageType.STREAM_DATA,
      payload,
    };

    const frame = encodeMessage(msg);
    const encrypted = this.psk ? this.encryptFrame(frame) : frame;
    await this.sock.send([this.streamId, encrypted]);
  }

  async end(): Promise<void> {
    const msg: Message = {
      header: {
        ver: 1,
        msgId: generateMsgId(),
        seq: 0,
        ts: Date.now(),
        traceId: generateTraceId(),
        contentType: 'application/json',
        encoding: 'utf-8',
        meta: { streamId: this.streamId },
      },
      type: MessageType.STREAM_END,
      payload: new Uint8Array(0),
    };

    const frame = encodeMessage(msg);
    const encrypted = this.psk ? this.encryptFrame(frame) : frame;
    await this.sock.send([this.streamId, encrypted]);
  }

  private encryptFrame(frame: Uint8Array): Uint8Array {
    if (!this.psk) return frame;
    const encrypted = encrypt(frame, this.psk);
    // 简化处理，实际应该打包 IV + AuthTag + Ciphertext
    return encrypted.ciphertext;
  }
}

/**
 * 流处理器内部类型
 */
interface StreamHandler {
  handler: StreamOptions;
  stream: Stream;
}

export { Stream };
