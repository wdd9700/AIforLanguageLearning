/**
 * @fileoverview 软总线集成模块 (Softbus Integration Module)
 * @description
 * 该模块负责 Electron 主进程与软总线 (Softbus) 的集成，实现跨进程/跨设备的高效通信。
 * 
 * 主要功能包括：
 * 1. 生命周期管理 (Lifecycle Management)：
 *    - 初始化 Softbus 客户端 (initializeSoftbus)
 *    - 连接/断开服务器
 *    - 应用退出时的资源清理 (cleanupSoftbus)
 * 
 * 2. IPC 桥接 (IPC Bridging)：
 *    - 将 Softbus 功能暴露给渲染进程 (publish, subscribe, rpc, stream)
 *    - 将 Softbus 事件转发给渲染进程 (softbus:message, softbus:stream-data)
 * 
 * 3. 流管理 (Stream Management)：
 *    - 维护活跃的数据流 (activeStreams)
 *    - 处理流数据的发送和接收
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import log from 'electron-log';
import { BrowserWindow, ipcMain } from 'electron';
import { SoftbusClient, Stream } from '../softbus/index.js';
import type { Message, PubSubOptions, RpcRequestOptions, StreamOptions } from '../softbus/types.js';

let softbusClient: SoftbusClient | null = null;
let mainWindow: BrowserWindow | null = null;
let activeStreams: Map<string, Stream> = new Map();

/**
 * 初始化 Softbus 客户端并绑定 IPC 处理程序
 * @param endpoint Softbus 服务端点 (例如 "tcp://localhost:5555")
 * @param clientWindow 用于 IPC 通信的主窗口
 * @param psk 可选的预共享密钥 (PSK) 用于加密
 */
export async function initializeSoftbus(endpoint: string, clientWindow: BrowserWindow, psk?: string): Promise<SoftbusClient> {
  mainWindow = clientWindow;
  
  try {
    log.info(`Softbus: Initializing client at ${endpoint}`);
    
    // 创建 SoftbusClient 实例
    softbusClient = new SoftbusClient({
      endpoint,
      psk,
      connectTimeout: 10000,
    });
    
    // 绑定事件监听器
    softbusClient.on((event: any) => {
      if (event.type === 'connected') {
        log.info('Softbus: Connected to server');
        mainWindow?.webContents.send('softbus:connected', {});
      } else if (event.type === 'disconnected') {
        log.warn('Softbus: Disconnected from server');
        mainWindow?.webContents.send('softbus:disconnected', {});
      } else if (event.type === 'error') {
        log.error('Softbus: Error', event.payload);
        mainWindow?.webContents.send('softbus:error', { message: String(event.payload) });
      }
    });
    
    // 连接到服务器
    await softbusClient.connect();
    log.info('Softbus: Connected successfully');
    
    return softbusClient;
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    log.error('Softbus initialization failed:', msg);
    throw error;
  }
}

/**
 * 发布消息到指定主题
 */
ipcMain.handle('softbus:publish', async (_event, payload: { topic: string; data: any; contentType?: string }) => {
  if (!softbusClient) return { ok: false, error: 'Softbus not initialized' };
  
  try {
    const data = typeof payload.data === 'string' 
      ? new TextEncoder().encode(payload.data)
      : new Uint8Array(payload.data);
    
    await softbusClient.publish(payload.topic, data, payload.contentType || 'application/octet-stream');
    
    return { ok: true };
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    log.error('softbus:publish error:', msg);
    return { ok: false, error: msg };
  }
});

/**
 * 订阅主题 (渲染进程将通过 IPC 接收消息)
 */
ipcMain.handle('softbus:subscribe', async (_event, payload: { topic: string }) => {
  if (!softbusClient) return { ok: false, error: 'Softbus not initialized' };
  
  try {
    const options: PubSubOptions = {
      topic: payload.topic,
      onMessage: (message: Message) => {
        // 通过 IPC 转发消息到渲染进程
        mainWindow?.webContents.send('softbus:message', {
          topic: payload.topic,
          msgId: message.header.msgId,
          payload: Array.from(message.payload),
          contentType: message.header.contentType,
        });
      },
    };
    
    softbusClient.subscribe(options);
    
    log.info(`Softbus: Subscribed to ${payload.topic}`);
    return { ok: true };
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    log.error('softbus:subscribe error:', msg);
    return { ok: false, error: msg };
  }
});

/**
 * 取消订阅主题
 */
ipcMain.handle('softbus:unsubscribe', async (_event, payload: { topic: string }) => {
  if (!softbusClient) return { ok: false, error: 'Softbus not initialized' };
  
  try {
    softbusClient.unsubscribe(payload.topic);
    log.info(`Softbus: Unsubscribed from ${payload.topic}`);
    return { ok: true };
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    log.error('softbus:unsubscribe error:', msg);
    return { ok: false, error: msg };
  }
});

/**
 * 发送 RPC 请求并等待响应
 */
ipcMain.handle('softbus:rpc', async (_event, payload: { method: string; params?: any; timeout?: number }) => {
  if (!softbusClient) return { ok: false, error: 'Softbus not initialized' };
  
  try {
    const options: RpcRequestOptions = {
      method: payload.method,
      params: payload.params || {},
      timeout: payload.timeout || 10000,
    };
    
    const response = await softbusClient.rpc(options);
    
    return {
      ok: true,
      data: response.data,
      success: response.success,
    };
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    log.error('softbus:rpc error:', msg);
    return { ok: false, error: msg };
  }
});

/**
 * 打开双向数据流
 */
ipcMain.handle('softbus:stream-open', async (_event, payload: { streamId: string; topic: string }) => {
  if (!softbusClient) return { ok: false, error: 'Softbus not initialized' };
  
  try {
    const options: StreamOptions = {
      streamId: payload.streamId,
      onData: (data: Uint8Array) => {
        mainWindow?.webContents.send('softbus:stream-data', {
          streamId: payload.streamId,
          data: Array.from(data),
        });
      },
      onClose: () => {
        mainWindow?.webContents.send('softbus:stream-end', {
          streamId: payload.streamId,
        });
        activeStreams.delete(payload.streamId);
      },
    };
    
    const stream = softbusClient.openStream(options);
    activeStreams.set(payload.streamId, stream);
    
    log.info(`Softbus: Opened stream ${payload.streamId}`);
    return { ok: true };
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    log.error('softbus:stream-open error:', msg);
    return { ok: false, error: msg };
  }
});

/**
 * 在打开的流上发送数据
 */
ipcMain.handle('softbus:stream-send', async (_event, payload: { streamId: string; data: any }) => {
  if (!softbusClient) return { ok: false, error: 'Softbus not initialized' };
  
  try {
    const stream = activeStreams.get(payload.streamId);
    if (!stream) return { ok: false, error: 'Stream not found' };
    
    const data = typeof payload.data === 'string'
      ? new TextEncoder().encode(payload.data)
      : new Uint8Array(payload.data);
    
    await stream.send(data);
    
    return { ok: true };
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    log.error('softbus:stream-send error:', msg);
    return { ok: false, error: msg };
  }
});

/**
 * 关闭流
 */
ipcMain.handle('softbus:stream-end', async (_event, payload: { streamId: string }) => {
  if (!softbusClient) return { ok: false, error: 'Softbus not initialized' };
  
  try {
    const stream = activeStreams.get(payload.streamId);
    if (!stream) return { ok: false, error: 'Stream not found' };
    
    await stream.end();
    activeStreams.delete(payload.streamId);
    
    return { ok: true };
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    log.error('softbus:stream-end error:', msg);
    return { ok: false, error: msg };
  }
});

/**
 * 断开 Softbus 连接
 */
ipcMain.handle('softbus:disconnect', async () => {
  if (!softbusClient) return { ok: false, error: 'Softbus not initialized' };
  
  try {
    // 关闭所有活跃的流
    for (const stream of activeStreams.values()) {
      try {
        await stream.end();
      } catch (e) {
        log.warn('Error closing stream:', e);
      }
    }
    activeStreams.clear();
    
    await softbusClient.disconnect();
    softbusClient = null;
    log.info('Softbus: Disconnected');
    return { ok: true };
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    log.error('softbus:disconnect error:', msg);
    return { ok: false, error: msg };
  }
});

/**
 * 获取 Softbus 连接状态
 */
ipcMain.handle('softbus:status', async () => {
  return {
    connected: softbusClient !== null,
  };
});

/**
 * 应用退出时清理资源
 */
export async function cleanupSoftbus(): Promise<void> {
  if (softbusClient) {
    try {
      // 关闭所有活跃的流
      for (const stream of activeStreams.values()) {
        try {
          await stream.end();
        } catch (e) {
          log.warn('Error closing stream during cleanup:', e);
        }
      }
      activeStreams.clear();
      
      await softbusClient.disconnect();
      softbusClient = null;
      log.info('Softbus: Cleaned up');
    } catch (error) {
      log.error('Softbus cleanup error:', error);
    }
  }
}
