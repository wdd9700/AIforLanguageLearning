/**
 * @fileoverview 全局错误处理中间件 (Global Error Handler)
 * @description
 * 该文件实现了 Express 应用的统一错误处理机制，确保所有未捕获的异常都能以标准化的 JSON 格式返回给客户端。
 * 
 * 主要功能：
 * 1. 错误工厂 (createError)：提供便捷的工具函数，用于创建带有 HTTP 状态码和业务错误码的自定义错误对象
 * 2. 统一捕获 (errorHandler)：
 *    - 捕获所有路由和中间件抛出的异常
 *    - 记录详细的错误日志（包含请求上下文、堆栈信息）
 *    - 格式化响应：{ success: false, error: { code, message, ... } }
 *    - 环境区分：在开发环境下返回堆栈信息，生产环境隐藏敏感细节
 * 3. 404 处理 (notFoundHandler)：处理所有未匹配路由的请求，返回标准的 404 响应
 * 
 * 待改进项：
 * - [ ] 集成 Sentry 等外部错误追踪服务
 * - [ ] 增加对异步 Promise Rejection 的全局捕获
 * - [ ] 实现错误分类统计和报警
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { Request, Response, NextFunction } from 'express';
import { createLogger } from '../utils/logger';

const logger = createLogger('ErrorHandler');

/**
 * 应用错误接口
 * 扩展标准 Error 对象，增加状态码和错误代码
 */
export interface AppError extends Error {
  statusCode?: number;
  code?: string;
  details?: any;
}

/**
 * 创建自定义错误对象
 * 
 * @param message 错误描述信息
 * @param statusCode HTTP 状态码，默认 500
 * @param code 业务错误代码，例如 'USER_NOT_FOUND'
 * @param details 额外的错误详情对象
 * @returns 构造好的 AppError 对象
 */
export function createError(
  message: string,
  statusCode: number = 500,
  code?: string,
  details?: any
): AppError {
  const error: AppError = new Error(message);
  error.statusCode = statusCode;
  error.code = code;
  error.details = details;
  return error;
}

/**
 * 错误处理中间件
 * Express 错误处理函数，必须包含 4 个参数
 */
export function errorHandler(
  err: AppError,
  req: Request,
  res: Response,
  next: NextFunction
): void {
  // 提取错误信息
  const statusCode = err.statusCode || 500;
  const code = err.code || 'INTERNAL_SERVER_ERROR';
  const message = err.message || 'An unexpected error occurred';

  // 记录错误日志
  logger.error(
    {
      method: req.method,
      path: req.path,
      statusCode,
      code,
      message,
      stack: err.stack,
      details: err.details,
    },
    'Request error'
  );

  // 返回标准化的错误响应
  res.status(statusCode).json({
    success: false,
    error: {
      code,
      message,
      // 开发环境下返回堆栈信息以便调试
      ...(process.env.NODE_ENV === 'development' && {
        stack: err.stack,
        details: err.details,
      }),
    },
  });
}

/**
 * 404 未找到处理中间件
 * 处理所有未匹配路由的请求
 */
export function notFoundHandler(req: Request, res: Response): void {
  res.status(404).json({
    success: false,
    error: {
      code: 'NOT_FOUND',
      message: `Route ${req.method} ${req.path} not found`,
    },
  });
}
