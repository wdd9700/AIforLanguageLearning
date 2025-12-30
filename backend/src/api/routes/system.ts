/**
 * @fileoverview 系统 API 路由 (System API Routes)
 * @description
 * 该文件定义了系统级别的 API 路由，提供健康检查、配置管理、服务控制和版本信息等功能。
 * 
 * 主要功能：
 * 1. 健康检查：监控所有后端服务（LLM, ASR, TTS, OCR）的运行状态
 * 2. 配置管理：查看和动态更新系统配置（支持持久化到 .env 文件）
 * 3. 服务控制：手动重启特定服务 (ASR, TTS)
 * 4. LLM 管理：列出可用模型、加载/卸载模型（支持高级参数配置）
 * 5. 场景扩展：辅助工具，将简短的场景描述扩展为详细的 System Prompt
 * 6. 版本信息：返回当前后端服务的版本号
 * 
 * 待改进项：
 * - [ ] 引入 WebSocket 推送实时健康状态
 * - [ ] 完善动态配置的热重载机制 (无需重启)
 * - [ ] 增加各服务的详细资源占用监控 (CPU/Memory)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { Router } from 'express';
import { ServiceManager } from '../../managers/service-manager';
import { SessionManager } from '../../managers/session-manager';
import { basicAuthMiddleware } from '../../middleware/basic-auth';
import { SystemController } from '../../controllers/system.controller';

/**
 * 创建系统路由
 */
export function createSystemRoutes(
  serviceManager: ServiceManager,
  sessionManager: SessionManager
): Router {
  const router = Router();
  const controller = new SystemController(serviceManager, sessionManager);

  // Health Check
  router.get('/health', controller.getHealth);

  // Configuration
  router.get('/config', controller.getConfig);
  router.post('/config', basicAuthMiddleware, controller.updateConfig);

  // Service Control
  router.post('/restart/:service', controller.restartService);
  router.post('/tts/start', (req, res) => controller.restartService({ ...req, params: { service: 'tts' } } as any, res));
  router.post('/asr/start', (req, res) => controller.restartService({ ...req, params: { service: 'asr' } } as any, res));

  // LLM Management
  router.get('/llm/models', controller.listModels);
  router.post('/llm/load', controller.loadModel);
  router.post('/llm/load-advanced', controller.loadModelAdvanced);
  router.post('/llm/unload', controller.unloadModel);

  // Utilities
  router.get('/version', (req, res) => {
    res.json({
      success: true,
      data: {
        name: 'AI Language Learning Platform',
        version: '1.0.0',
        apiVersion: 'v1',
      },
    });
  });
  
  router.post('/expand-scenario', controller.expandScenario);
  router.get('/service-params', controller.getServiceParams);

  return router;
}
