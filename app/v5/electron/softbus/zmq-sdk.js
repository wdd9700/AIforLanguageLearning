/**
 * Softbus - ZeroMQ-based P2P Message Bus
 * ZMQ SDK Wrapper (Pub/Sub, RPC, Streams)
 */
import zmq from 'zeromq';
import { MessageType } from './types.js';
import { encodeMessage, decodeMessage, generateMsgId, generateTraceId, parseErrorMessage } from './protocol.js';
import { encrypt, decrypt } from './crypto.js';
/**
 * Softbus Client (ZMQ 包装器)
 */
export class SoftbusClient {
    endpoint;
    psk;
    sock; // zmq.Socket (native module, no type definitions)
    subscribers = new Map();
    rpcCallbacks = new Map();
    streams = new Map();
    eventHandlers = [];
    heartbeatTimer;
    reconnectTimer;
    isConnected = false;
    constructor(options) {
        this.endpoint = options.endpoint;
        this.psk = options.psk;
    }
    /**
     * 连接到软总线
     */
    async connect() {
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
        }
        catch (err) {
            console.error('[softbus] connect error:', err);
            this.emit({ type: 'error', payload: err, timestamp: Date.now() });
            throw err;
        }
    }
    /**
     * 断开连接
     */
    async disconnect() {
        if (this.heartbeatTimer)
            clearInterval(this.heartbeatTimer);
        if (this.reconnectTimer)
            clearInterval(this.reconnectTimer);
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
    async publish(topic, payload, contentType = 'application/octet-stream') {
        if (!this.sock || !this.isConnected) {
            throw new Error('Not connected');
        }
        const msg = {
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
    subscribe(options) {
        const { topic, onMessage, onError } = options;
        this.subscribers.set(topic, onMessage || (() => { }));
    }
    /**
     * 取消订阅
     */
    unsubscribe(topic) {
        this.subscribers.delete(topic);
    }
    /**
     * 发送 RPC 请求
     */
    async rpc(options) {
        if (!this.sock || !this.isConnected) {
            throw new Error('Not connected');
        }
        const msgId = generateMsgId();
        const payload = new TextEncoder().encode(JSON.stringify(options.params || {}));
        const msg = {
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
    openStream(options) {
        const stream = new Stream(options.streamId, this.sock, this.psk);
        this.streams.set(options.streamId, { handler: options, stream });
        return stream;
    }
    /**
     * 注册事件监听器
     */
    on(handler) {
        this.eventHandlers.push(handler);
    }
    /**
     * 发出事件
     */
    emit(event) {
        for (const handler of this.eventHandlers) {
            try {
                handler(event);
            }
            catch (err) {
                console.error('[softbus] event handler error:', err);
            }
        }
    }
    /**
     * 启动消息接收循环
     */
    async startReceiving() {
        if (!this.sock)
            return;
        try {
            for await (const [topic, frame] of this.sock) {
                try {
                    // 解密（如果需要）
                    const decrypted = this.psk ? this.decryptFrame(frame) : frame;
                    if (!decrypted)
                        continue;
                    // 解码消息
                    const result = decodeMessage(decrypted);
                    if (!result)
                        continue;
                    const { message } = result;
                    // 根据消息类型分发
                    switch (message.type) {
                        case MessageType.PUB: {
                            const handler = this.subscribers.get(topic);
                            if (handler)
                                handler(message);
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
                }
                catch (err) {
                    console.error('[softbus] message processing error:', err);
                }
            }
        }
        catch (err) {
            console.error('[softbus] receiving error:', err);
            this.isConnected = false;
            this.emit({ type: 'disconnected', timestamp: Date.now() });
        }
    }
    /**
     * 启动心跳
     */
    startHeartbeat() {
        this.heartbeatTimer = setInterval(async () => {
            if (!this.sock || !this.isConnected)
                return;
            try {
                const msg = {
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
            }
            catch (err) {
                console.error('[softbus] heartbeat error:', err);
            }
        }, 30000); // 30 秒一次
    }
    /**
     * 加密帧
     */
    encryptFrame(frame) {
        if (!this.psk)
            return frame;
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
    decryptFrame(frame) {
        if (!this.psk)
            return frame;
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
        }
        catch (err) {
            console.error('[softbus] decrypt error:', err);
            return null;
        }
    }
}
/**
 * 双向流处理器
 */
class Stream {
    streamId;
    sock;
    psk;
    constructor(streamId, sock, // zmq.Socket (native module, no type definitions)
    psk) {
        this.streamId = streamId;
        this.sock = sock;
        this.psk = psk;
    }
    async send(payload) {
        const msg = {
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
    async end() {
        const msg = {
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
    encryptFrame(frame) {
        if (!this.psk)
            return frame;
        const encrypted = encrypt(frame, this.psk);
        // 简化处理，实际应该打包 IV + AuthTag + Ciphertext
        return encrypted.ciphertext;
    }
}
export { Stream };
//# sourceMappingURL=zmq-sdk.js.map