/**
 * @fileoverview 认证控制器 (Auth Controller)
 * @description
 * 处理用户认证相关的 HTTP 请求，包括注册、登录、刷新 Token 和获取当前用户信息。
 * 负责参数验证、调用 UserModel 进行数据操作，并生成 JWT 令牌。
 */

import { Request, Response, NextFunction } from 'express';
import { UserModel } from '../models/user';
import { generateTokenPair, verifyRefreshToken } from '../auth/jwt';
import { validatePasswordStrength } from '../auth/password';
import { createError } from '../middleware/error-handler';
import { AuthRequest } from '../middleware/auth';
import { Database } from '../database/db';
import { createLogger } from '../utils/logger';

const logger = createLogger('AuthController');

export class AuthController {
  private userModel: UserModel;

  constructor(db: Database) {
    this.userModel = new UserModel(db);
  }

  /**
   * 处理用户注册请求
   * 
   * 1. 验证必填字段 (username, email, password)。
   * 2. 验证密码强度。
   * 3. 调用 UserModel 创建新用户。
   * 4. 生成 Access Token 和 Refresh Token。
   * 5. 返回用户信息和 Token 对。
   */
  public register = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { username, email, password } = req.body;

      // 参数验证
      if (!username || !email || !password) {
        throw createError('缺少必填字段', 400, 'VALIDATION_ERROR');
      }

      // 验证密码强度
      const passwordValidation = validatePasswordStrength(password);
      if (!passwordValidation.valid) {
        throw createError(
          passwordValidation.message || '密码强度不足',
          400,
          'WEAK_PASSWORD'
        );
      }

      // 创建用户
      const user = await this.userModel.create({ username, email, password });

      // 生成 token
      const tokens = generateTokenPair({
        userId: user.id,
        username: user.username,
      });

      logger.info({ userId: user.id, username: user.username }, '用户注册成功');

      res.status(201).json({
        success: true,
        data: {
          user: {
            id: user.id,
            username: user.username,
            email: user.email,
          },
          ...tokens,
        },
      });
    } catch (error: any) {
      next(error);
    }
  };

  /**
   * 处理用户登录请求
   * 
   * 1. 验证必填字段。
   * 2. 调用 UserModel.verifyCredentials 验证用户名和密码。
   * 3. 验证成功后生成 Token 对。
   * 4. 返回用户信息和 Token。
   */
  public login = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { username, password } = req.body;

      // 参数验证
      if (!username || !password) {
        throw createError('缺少用户名或密码', 400, 'VALIDATION_ERROR');
      }

      // 验证凭据
      const user = await this.userModel.verifyCredentials(username, password);
      if (!user) {
        throw createError('用户名或密码错误', 401, 'INVALID_CREDENTIALS');
      }

      // 生成 token
      const tokens = generateTokenPair({
        userId: user.id,
        username: user.username,
      });

      logger.info({ userId: user.id, username: user.username }, '用户登录成功');

      res.json({
        success: true,
        data: {
          user: {
            id: user.id,
            username: user.username,
            email: user.email,
          },
          ...tokens,
        },
      });
    } catch (error: any) {
      next(error);
    }
  };

  /**
   * 刷新访问令牌 (Refresh Token)
   * 
   * 当 Access Token 过期时，使用 Refresh Token 获取新的 Token 对。
   * 1. 验证 Refresh Token 的有效性。
   * 2. 如果有效，生成新的 Access Token 和 Refresh Token。
   */
  public refresh = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { refreshToken } = req.body;

      if (!refreshToken) {
        throw createError('缺少刷新令牌', 400, 'VALIDATION_ERROR');
      }

      // 验证刷新令牌
      const payload = verifyRefreshToken(refreshToken);
      if (!payload) {
        throw createError('无效的刷新令牌', 401, 'INVALID_TOKEN');
      }

      // 生成新的 token 对
      const tokens = generateTokenPair({
        userId: payload.userId,
        username: payload.username,
      });

      res.json({
        success: true,
        data: tokens,
      });
    } catch (error: any) {
      next(error);
    }
  };

  /**
   * 用户登出
   * 
   * 目前仅在客户端清除 Token。
   * TODO: 在服务端实现 Token 黑名单机制以支持强制登出。
   */
  public logout = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      // 在实际应用中，这里可以将 token 加入黑名单
      // 目前简单返回成功

      logger.info({ userId: req.userId }, '用户登出');

      res.json({
        success: true,
        message: '登出成功',
      });
    } catch (error: any) {
      next(error);
    }
  };

  /**
   * 获取当前用户信息
   * 
   * 根据请求头中的 Access Token 获取当前登录用户的详细信息。
   */
  public getMe = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      if (!req.userId) {
        throw createError('用户未认证', 401, 'UNAUTHORIZED');
      }

      const user = await this.userModel.findById(req.userId);
      if (!user) {
        throw createError('用户不存在', 404, 'USER_NOT_FOUND');
      }

      res.json({
        success: true,
        data: {
          id: user.id,
          username: user.username,
          email: user.email,
          createdAt: user.created_at,
        },
      });
    } catch (error: any) {
      next(error);
    }
  };
}
