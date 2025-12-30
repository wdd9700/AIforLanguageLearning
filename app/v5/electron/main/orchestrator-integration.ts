/**
 * @fileoverview 编排器集成模块 (Orchestrator Integration Module)
 * @description
 * 该模块负责将服务编排器 (ServiceOrchestrator) 集成到 Electron 主进程中，并连接到软总线。
 * 
 * 主要功能包括：
 * 1. 初始化与集成 (Initialization & Integration)：
 *    - 创建 ServiceOrchestrator 实例
 *    - 将编排器连接到 SoftbusClient
 *    - 订阅路由模式并将消息转发给编排器
 * 
 * 2. 消息处理 (Message Handling)：
 *    - 接收 Softbus 消息并调用 orchestrator.handleMessage
 *    - 将处理结果返回给 Softbus (发布到 res/ 主题)
 *    - 将结果和错误转发给渲染进程
 * 
 * 3. IPC 接口 (IPC Interface)：
 *    - 获取编排器状态、服务状态和指标 (status, services, metrics)
 *    - 手动执行 Pipeline (execute-pipeline)
 *    - 直接发送消息到服务 (send)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import log from 'electron-log';
import { BrowserWindow, ipcMain } from 'electron';
import { SoftbusClient } from '../softbus/index.js';
import { ServiceOrchestrator, OrchestratorConfig } from '../orchestration/index.js';

let orchestrator: ServiceOrchestrator | null = null;
let softbusClient: SoftbusClient | null = null;
let mainWindow: BrowserWindow | null = null;

/**
 * 初始化编排器并集成软总线
 * @param orchestratorConfig 编排器配置
 * @param clientWindow 用于 IPC 通信的主窗口
 * @param client 已连接的 Softbus 客户端
 */
export async function initializeOrchestrator(
  orchestratorConfig: OrchestratorConfig,
  clientWindow: BrowserWindow,
  client: SoftbusClient
): Promise<void> {
  mainWindow = clientWindow;
  softbusClient = client;

  try {
    log.info('Initializing ServiceOrchestrator with Softbus integration...');

    // 创建编排器实例
    orchestrator = new ServiceOrchestrator(orchestratorConfig);

    // 将编排器事件转发到渲染进程
    orchestrator.on('started', () => {
      log.info('Orchestrator started');
      mainWindow?.webContents.send('orchestrator:started', {});
    });

    orchestrator.on('stopped', () => {
      log.info('Orchestrator stopped');
      mainWindow?.webContents.send('orchestrator:stopped', {});
    });

    // 订阅 Softbus 主题并将消息路由到编排器
    for (const pattern of orchestratorConfig.routes) {
      subscribeToTopic(pattern.pattern);
    }

    // 启动编排器
    await orchestrator.start();

    log.info('ServiceOrchestrator initialized successfully');
  } catch (error: any) {
    log.error('Failed to initialize orchestrator:', error);
    throw error;
  }
}

/**
 * 订阅 Softbus 主题并路由到编排器
 * @param pattern 路由模式
 */
function subscribeToTopic(pattern: string): void {
  if (!softbusClient) return;

  // 如果需要，将编排器模式转换为 Softbus 模式
  // 例如: '#' -> 'svc/*'
  const topic = pattern.replace('#', 'svc/*');

  softbusClient.subscribe({
    topic,
    onMessage: async (message: any) => {
      if (!orchestrator) return;

      try {
        // 让编排器处理消息
        const result = await orchestrator.handleMessage(
          topic,
          message.payload,
          message.header.contentType
        );

        // 将处理结果发送回 Softbus (发布到 res/ 原主题)
        if (softbusClient) {
          const resultJson = JSON.stringify(result);
          const resultBuffer = new TextEncoder().encode(resultJson);
          await softbusClient.publish(
            `res/${topic}`,
            resultBuffer,
            'application/json'
          );
        }

        // 转发结果到渲染进程用于 UI 更新
        mainWindow?.webContents.send('orchestrator:result', {
          topic,
          result,
        });
      } catch (error: any) {
        log.error('Error handling message:', error);
        mainWindow?.webContents.send('orchestrator:error', {
          topic,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    },
  });

  log.info(`Subscribed to topic: ${topic}`);
}

/**
 * IPC 处理程序: 获取编排器状态
 */
ipcMain.handle('orchestrator:status', async () => {
  if (!orchestrator) return { ok: false, error: 'Orchestrator not initialized' };

  return {
    ok: true,
    services: orchestrator.getServiceStates(),
    metrics: orchestrator.getMetrics(),
    pipelines: orchestrator.getPipelines(),
  };
});

/**
 * IPC 处理程序: 获取服务状态
 */
ipcMain.handle('orchestrator:services', async () => {
  if (!orchestrator) return { ok: false, error: 'Orchestrator not initialized' };

  return {
    ok: true,
    services: orchestrator.getServiceStates(),
  };
});

/**
 * IPC 处理程序: 获取指标数据
 */
ipcMain.handle('orchestrator:metrics', async () => {
  if (!orchestrator) return { ok: false, error: 'Orchestrator not initialized' };

  return {
    ok: true,
    metrics: orchestrator.getMetrics(),
  };
});

/**
 * IPC 处理程序: 执行 Pipeline
 */
ipcMain.handle('orchestrator:execute-pipeline', async (_event: any, payload: { name: string; data: any }) => {
  if (!orchestrator) return { ok: false, error: 'Orchestrator not initialized' };

  try {
    const result = await orchestrator.executePipeline(payload.name, payload.data);
    return { ok: true, result };
  } catch (error: any) {
    const msg = error instanceof Error ? error.message : String(error);
    log.error('Pipeline execution failed:', msg);
    return { ok: false, error: msg };
  }
});

/**
 * IPC 处理程序: 发送消息到服务 (直接调用)
 */
ipcMain.handle('orchestrator:send', async (_event: any, payload: { topic: string; data: any; contentType?: string }) => {
  if (!orchestrator) return { ok: false, error: 'Orchestrator not initialized' };

  try {
    const result = await orchestrator.handleMessage(
      payload.topic,
      payload.data,
      payload.contentType || 'application/octet-stream'
    );
    return { ok: true, result };
  } catch (error: any) {
    const msg = error instanceof Error ? error.message : String(error);
    log.error('Message handling failed:', msg);
    return { ok: false, error: msg };
  }
});

/**
 * 清理编排器资源
 */
export async function cleanupOrchestrator(): Promise<void> {
  if (orchestrator) {
    try {
      await orchestrator.cleanup?.();
      orchestrator = null;
      log.info('Orchestrator cleaned up');
    } catch (error: any) {
      log.error('Orchestrator cleanup error:', error);
    }
  }
}

