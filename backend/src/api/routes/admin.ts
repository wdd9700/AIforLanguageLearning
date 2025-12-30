/**
 * @fileoverview 管理员 API 路由 (Admin API Routes)
 * @description
 * 该文件定义了管理员专用的 API 路由，提供系统配置、服务监控、日志查看、备份恢复等高级管理功能。
 * 
 * 主要功能：
 * 1. 系统配置管理：查看和更新全局配置、Prompt 模板
 * 2. 服务监控：查看 AI 服务状态和配置
 * 3. 备份管理：列出、创建和恢复数据库备份
 * 4. 日志管理：查看和清空系统日志
 * 5. 安全工具：提供文本加密测试接口 (KMS)
 * 6. 系统状态：获取操作系统和进程级别的性能指标
 * 7. 维护工具：触发临时文件清理
 * 8. 用户管理：列出用户、重置密码、删除用户
 * 
 * 安全性：
 * - 所有路由均受 Basic Auth 中间件保护
 * - 仅限授权管理员访问
 * 
 * 待改进项：
 * - [ ] 实现基于角色的访问控制 (RBAC)，细化管理员权限
 * - [ ] 增加管理操作审计日志 (Audit Log)
 * - [ ] 提供更详细的实时性能监控图表数据接口
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { Router } from 'express';
import { ServiceManager } from '../../managers/service-manager';
import { Database } from '../../database/db';
import { basicAuthMiddleware } from '../../middleware/basic-auth';
import { AdminController } from '../../controllers/admin.controller';

export function createAdminRoutes(db: Database, serviceManager: ServiceManager): Router {
  const router = Router();
  const adminController = new AdminController(db, serviceManager);

  // 所有管理路由应用 Basic Auth 认证
  router.use(basicAuthMiddleware);

  /**
   * GET /api/admin/config
   * 获取完整系统配置
   */
  router.get('/config', adminController.getConfig);

  /**
   * POST /api/admin/config
   * 更新系统配置
   */
  router.post('/config', adminController.updateConfig);

  /**
   * GET /api/admin/prompts
   * 获取所有 Prompt 模板
   */
  router.get('/prompts', adminController.getPrompts);

  /**
   * POST /api/admin/prompts/:category
   * 更新特定类别的 Prompt
   */
  router.post('/prompts/:category', adminController.updatePrompt);

  /**
   * GET /api/admin/services
   * 获取服务状态和配置
   */
  router.get('/services', adminController.getServices);

  // --- 备份管理 ---

  /**
   * GET /api/admin/backups
   * 列出所有备份
   */
  router.get('/backups', adminController.listBackups);

  /**
   * POST /api/admin/backups
   * 创建新备份 (手动触发)
   */
  router.post('/backups', adminController.createBackup);

  /**
   * POST /api/admin/backups/restore
   * 恢复备份
   */
  router.post('/backups/restore', adminController.restoreBackup);

  // --- 日志管理 ---

  /**
   * GET /api/admin/logs
   * 获取最近的日志 (最后 100 行)
   */
  router.get('/logs', adminController.getLogs);

  /**
   * DELETE /api/admin/logs
   * 清空日志
   */
  router.delete('/logs', adminController.clearLogs);

  // --- 安全 / KMS ---

  /**
   * POST /api/admin/encrypt
   * 加密文本 (测试/工具用途)
   */
  router.post('/encrypt', adminController.encryptText);

  // --- 系统状态 ---

  /**
   * GET /api/admin/system-stats
   * 获取操作系统级别的状态信息
   */
  router.get('/system-stats', adminController.getSystemStats);

  // --- 清理 ---

  /**
   * POST /api/admin/cleanup
   * 触发临时文件清理
   */
  router.post('/cleanup', adminController.cleanup);

  // --- 用户管理 ---

  /**
   * GET /api/admin/users
   * 列出所有用户
   */
  router.get('/users', adminController.listUsers);

  /**
   * POST /api/admin/users/:id/reset-password
   * 重置用户密码
   */
  router.post('/users/:id/reset-password', adminController.resetUserPassword);

  /**
   * DELETE /api/admin/users/:id
   * 删除用户
   */
  router.delete('/users/:id', adminController.deleteUser);

  return router;
}
