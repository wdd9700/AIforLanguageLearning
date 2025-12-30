/**
 * Softbus - ZeroMQ-based P2P Message Bus
 * ZMQ SDK Wrapper (Pub/Sub, RPC, Streams)
 */
import { ConnectOptions, PubSubOptions, RpcRequestOptions, StreamOptions, BusEvent, RpcResponse } from './types.js';
/**
 * Softbus Client (ZMQ 包装器)
 */
export declare class SoftbusClient {
    private endpoint;
    private psk?;
    private sock?;
    private subscribers;
    private rpcCallbacks;
    private streams;
    private eventHandlers;
    private heartbeatTimer?;
    private reconnectTimer?;
    private isConnected;
    constructor(options: ConnectOptions);
    /**
     * 连接到软总线
     */
    connect(): Promise<void>;
    /**
     * 断开连接
     */
    disconnect(): Promise<void>;
    /**
     * 发布消息
     */
    publish(topic: string, payload: Uint8Array, contentType?: string): Promise<void>;
    /**
     * 订阅主题
     */
    subscribe(options: PubSubOptions): void;
    /**
     * 取消订阅
     */
    unsubscribe(topic: string): void;
    /**
     * 发送 RPC 请求
     */
    rpc(options: RpcRequestOptions): Promise<RpcResponse>;
    /**
     * 打开双向流
     */
    openStream(options: StreamOptions): Stream;
    /**
     * 注册事件监听器
     */
    on(handler: (event: BusEvent) => void): void;
    /**
     * 发出事件
     */
    private emit;
    /**
     * 启动消息接收循环
     */
    private startReceiving;
    /**
     * 启动心跳
     */
    private startHeartbeat;
    /**
     * 加密帧
     */
    private encryptFrame;
    /**
     * 解密帧
     */
    private decryptFrame;
}
/**
 * 双向流处理器
 */
declare class Stream {
    private streamId;
    private sock;
    private psk?;
    constructor(streamId: string, sock: any, // zmq.Socket (native module, no type definitions)
    psk?: string | undefined);
    send(payload: Uint8Array): Promise<void>;
    end(): Promise<void>;
    private encryptFrame;
}
export { Stream };
//# sourceMappingURL=zmq-sdk.d.ts.map