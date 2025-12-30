/**
 * @fileoverview JWT 认证模块 (JWT Authentication)
 * @description
 * 该文件封装了 JSON Web Token (JWT) 的生成、验证和刷新逻辑，实现了基于 Token 的无状态认证机制。
 * 
 * 主要功能：
 * 1. Token 生成：
 *    - Access Token：短期有效，用于 API 访问鉴权
 *    - Refresh Token：长期有效，用于在 Access Token 过期后获取新 Token
 * 2. Token 验证：校验 Token 的签名、有效期和完整性
 * 3. Token 刷新：实现无感知的会话续期
 * 4. 工具函数：解析时间字符串（如 "7d", "24h"）为秒数
 * 
 * 安全性：
 * - 使用环境变量中的密钥 (config.jwt.secret) 进行签名
 * - 区分 Access Token 和 Refresh Token 的有效期
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import jwt from 'jsonwebtoken';
import { config } from '../config/env';
import { createLogger } from '../utils/logger';

const logger = createLogger('JWT');

/**
 * JWT 载荷接口
 * 定义 Token 中包含的用户信息
 */
interface TokenPayload {
  userId: number;
  username: string;
}

/**
 * Token 对接口
 * 包含访问令牌、刷新令牌和过期时间
 */
export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

/**
 * 生成访问令牌 (Access Token)
 * 用于短期认证
 * 
 * @param payload 用户信息载荷
 * @returns 签名的 JWT 字符串
 */
export function generateAccessToken(payload: TokenPayload): string {
  return jwt.sign(payload, config.jwt.secret, {
    expiresIn: config.jwt.expiresIn,
  } as jwt.SignOptions);
}

/**
 * 生成刷新令牌 (Refresh Token)
 * 用于长期保持登录状态，换取新的 Access Token
 * 
 * @param payload 用户信息载荷
 * @returns 签名的 JWT 字符串
 */
export function generateRefreshToken(payload: TokenPayload): string {
  return jwt.sign(payload, config.jwt.secret, {
    expiresIn: config.jwt.refreshExpiresIn,
  } as jwt.SignOptions);
}

/**
 * 生成 Token 对
 * 同时生成 Access Token 和 Refresh Token
 * 
 * @param payload 用户信息载荷
 * @returns 包含双 Token 和过期信息的对象
 */
export function generateTokenPair(payload: TokenPayload): TokenPair {
  const accessToken = generateAccessToken(payload);
  const refreshToken = generateRefreshToken(payload);

  // 计算过期时间（秒） - 解析类似 "7d"、"24h" 或纯数字（秒）
  const parseDurationToSeconds = (s: string): number => {
    if (!s) return 0;
    const m = s.match(/^(\d+)([smhd])?$/i);
    if (!m) return 0;
    const v = parseInt(m[1], 10);
    const unit = (m[2] || 's').toLowerCase();
    switch (unit) {
      case 's':
        return v;
      case 'm':
        return v * 60;
      case 'h':
        return v * 3600;
      case 'd':
        return v * 86400;
      default:
        return v;
    }
  };

  const expiresIn = parseDurationToSeconds(config.jwt.expiresIn);

  return {
    accessToken,
    refreshToken,
    expiresIn,
  };
}

/**
 * 验证访问令牌
 * 检查 Token 签名和有效期
 * 
 * @param token JWT 字符串
 * @returns 解码后的载荷，验证失败返回 null
 */
export function verifyAccessToken(token: string): TokenPayload | null {
  try {
    const payload = jwt.verify(token, config.jwt.secret) as TokenPayload;
    return payload;
  } catch (error: any) {
    logger.warn({ error: error.message }, 'Access token verification failed');
    return null;
  }
}

/**
 * 验证刷新令牌
 * 
 * @param token JWT 字符串
 * @returns 解码后的载荷，验证失败返回 null
 */
export function verifyRefreshToken(token: string): TokenPayload | null {
  try {
    const payload = jwt.verify(token, config.jwt.secret) as TokenPayload;
    return payload;
  } catch (error: any) {
    logger.warn({ error: error.message }, 'Refresh token verification failed');
    return null;
  }
}

/**
 * 刷新访问令牌
 * 使用有效的 Refresh Token 获取新的 Access Token
 * 
 * @param refreshToken 刷新令牌
 * @returns 新的 Access Token，失败返回 null
 */
export function refreshAccessToken(refreshToken: string): string | null {
  const payload = verifyRefreshToken(refreshToken);
  if (!payload) {
    return null;
  }

  // 生成新的访问令牌
  return generateAccessToken({ userId: payload.userId, username: payload.username });
}
