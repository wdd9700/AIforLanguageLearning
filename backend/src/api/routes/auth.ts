/**
 * @fileoverview 认证 API 路由 (Auth API Routes)
 * @description
 * 该文件定义了用户认证相关的 API 路由，处理注册、登录、令牌刷新和用户信息获取等操作。
 * 
 * 主要功能：
 * 1. 用户注册：验证输入、检查密码强度、创建新用户并返回初始 Token
 * 2. 用户登录：验证凭据、生成 Access/Refresh Token 对
 * 3. 令牌刷新：使用 Refresh Token 获取新的 Access Token，延长会话有效期
 * 4. 用户登出：处理登出逻辑（如 Token 黑名单，目前仅做日志记录）
 * 5. 个人信息：获取当前经过身份验证的用户的详细资料
 * 
 * 安全性：
 * - 敏感操作（如获取个人信息）受 JWT 认证中间件保护
 * - 密码在存储前经过哈希处理（由 UserModel 处理）
 * - 输入参数经过严格验证
 * 
 * 待改进项：
 * - [ ] 增加登录接口的速率限制 (Rate Limiting) 防止暴力破解
 * - [ ] 实现邮箱验证流程
 * - [ ] 支持双因素认证 (2FA)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { Router } from 'express';
import { AuthController } from '../../controllers/auth.controller';
import { authMiddleware } from '../../middleware/auth';
import { Database } from '../../database/db';

/**
 * 创建认证路由
 * 
 * @param db 数据库实例
 * @returns Express Router 对象
 */
export function createAuthRoutes(db: Database): Router {
  const router = Router();
  const authController = new AuthController(db);

  /**
   * POST /api/auth/register
   * 用户注册接口
   */
  router.post('/register', authController.register);

  /**
   * POST /api/auth/login
   * 用户登录接口
   */
  router.post('/login', authController.login);

  /**
   * POST /api/auth/refresh
   * 刷新访问令牌接口
   */
  router.post('/refresh', authController.refresh);

  /**
   * POST /api/auth/logout
   * 用户登出接口（需要认证）
   */
  router.post('/logout', authMiddleware, authController.logout);

  /**
   * GET /api/auth/me
   * 获取当前用户信息接口（需要认证）
   */
  router.get('/me', authMiddleware, authController.getMe);

  return router;
}
