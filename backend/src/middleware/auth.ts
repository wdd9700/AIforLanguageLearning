/**
 * @fileoverview 认证中间件 (Authentication Middleware)
 * @description
 * 该文件实现了基于 JWT (JSON Web Token) 的请求认证机制，用于保护 API 路由。
 * 
 * 主要功能：
 * 1. 强制认证 (authMiddleware)：
 *    - 检查 Authorization 头是否存在 Bearer Token
 *    - 验证 Token 的签名和有效期
 *    - 将解码后的用户信息 (userId, username) 注入到 req 对象中
 *    - 验证失败时抛出 401 Unauthorized 错误
 * 2. 可选认证 (optionalAuthMiddleware)：
 *    - 尝试验证 Token，如果成功则注入用户信息
 *    - 如果 Token 缺失或无效，不抛出错误，允许请求继续（适用于公开但可个性化的接口）
 * 3. 类型扩展：定义 AuthRequest 接口，扩展 Express Request 以包含用户属性
 * 
 * 待改进项：
 * - [ ] 增加 Token 黑名单检查 (Redis) 以支持立即登出
 * - [ ] 支持 OAuth2 / OpenID Connect 等第三方登录标准
 * - [ ] 细化权限控制 (Scope/Role based access control)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { createLogger } from '../utils/logger';
import { config } from '../config/env';
import { createError } from './error-handler';

const logger = createLogger('Auth');

/**
 * 扩展 Request 接口
 * 在 Express 请求对象中添加用户认证信息
 */
export interface AuthRequest extends Request {
  userId?: number;
  username?: string;
  body: any;
  query: any;
  headers: any;
}

/**
 * JWT 载荷接口
 * 定义 Token 解码后的数据结构
 */
interface JWTPayload {
  userId: number;
  username: string;
  iat: number;
  exp: number;
}

/**
 * 强制认证中间件
 * 验证 Authorization 头中的 Bearer Token
 * 如果验证失败，将抛出 401 错误
 */
export function authMiddleware(req: AuthRequest, res: Response, next: NextFunction): void {
  try {
    // 从 Authorization header 获取 token
    const authHeader = req.headers.authorization;
    if (!authHeader) {
      throw createError('Missing authorization header', 401, 'UNAUTHORIZED');
    }

    // 验证 token 格式
    const parts = authHeader.split(' ');
    if (parts.length !== 2 || parts[0] !== 'Bearer') {
      throw createError('Invalid authorization header format', 401, 'UNAUTHORIZED');
    }

    const token = parts[1];

    // 验证 token
    const payload = jwt.verify(token, config.jwt.secret) as JWTPayload;

    // 注入用户信息到请求对象
    req.userId = payload.userId;
    req.username = payload.username;

    logger.debug({ userId: payload.userId, username: payload.username }, 'User authenticated');

    next();
  } catch (error: any) {
    if (error.name === 'JsonWebTokenError') {
      next(createError('Invalid token', 401, 'INVALID_TOKEN'));
    } else if (error.name === 'TokenExpiredError') {
      next(createError('Token expired', 401, 'TOKEN_EXPIRED'));
    } else {
      next(error);
    }
  }
}

/**
 * 可选认证中间件
 * 尝试验证 Token，如果验证成功则注入用户信息
 * 如果 Token 不存在或无效，不会报错，继续执行后续逻辑
 */
export function optionalAuthMiddleware(req: AuthRequest, res: Response, next: NextFunction): void {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader) {
      return next();
    }

    const parts = authHeader.split(' ');
    if (parts.length !== 2 || parts[0] !== 'Bearer') {
      return next();
    }

    const token = parts[1];
    const payload = jwt.verify(token, config.jwt.secret) as JWTPayload;

    req.userId = payload.userId;
    req.username = payload.username;

    next();
  } catch (error: any) {
    // 忽略错误，继续处理请求
    next();
  }
}
