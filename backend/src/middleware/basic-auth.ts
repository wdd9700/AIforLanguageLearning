/**
 * @fileoverview Basic Auth 认证中间件 (Basic Authentication Middleware)
 * @description
 * 该文件实现了 HTTP Basic Authentication 机制，主要用于保护系统管理接口 (Admin API)。
 * 
 * 主要功能：
 * 1. 凭据验证：解析 Authorization 头中的 Base64 编码凭据 (username:password)
 * 2. 权限控制：比对凭据与系统配置 (config.admin) 中的管理员账号密码
 * 3. 响应处理：
 *    - 验证通过：放行请求 (next)
 *    - 缺失凭据：返回 401 Unauthorized 并设置 WWW-Authenticate 头
 *    - 凭据错误：返回 403 Forbidden
 * 
 * 适用场景：
 * - /api/admin/* 路由
 * - 系统配置更新接口
 * - 服务重启接口
 * 
 * 待改进项：
 * - [ ] 支持多管理员账号配置
 * - [ ] 增加 IP 白名单限制
 * - [ ] 迁移至更安全的认证方式 (如 mTLS 或 API Key)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { Request, Response, NextFunction } from 'express';
import { config } from '../config/env';

/**
 * Basic Auth 认证中间件
 * 用于保护管理员路由
 */
export function basicAuthMiddleware(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;

  if (!authHeader) {
    res.setHeader('WWW-Authenticate', 'Basic realm="Admin Area"');
    return res.status(401).json({ error: 'Authentication required' });
  }

  const [scheme, credentials] = authHeader.split(' ');

  if (scheme !== 'Basic' || !credentials) {
    return res.status(401).json({ error: 'Invalid authentication format' });
  }

  // 解码 Base64 凭据 (username:password)
  const [username, password] = Buffer.from(credentials, 'base64').toString().split(':');

  const adminUser = config.admin.user;
  const adminPass = config.admin.password;

  if (username === adminUser && password === adminPass) {
    return next();
  }

  return res.status(403).json({ error: 'Invalid credentials' });
}
