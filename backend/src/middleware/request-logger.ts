/**
 * @fileoverview 请求日志中间件 (Request Logger Middleware)
 * @description
 * 该文件实现了 HTTP 请求的审计日志功能，用于监控系统流量和排查问题。
 * 
 * 主要功能：
 * 1. 入站记录：在请求到达时记录方法、路径、查询参数、客户端 IP 和 User-Agent
 * 2. 出站记录：在响应发送完毕 (finish 事件) 后记录 HTTP 状态码和请求处理耗时 (Duration)
 * 3. 结构化日志：使用 JSON 格式记录，便于后续通过日志分析工具进行聚合和查询
 * 
 * 待改进项：
 * - [ ] 增加请求体 (Body) 的脱敏记录 (需注意性能和隐私)
 * - [ ] 支持采样记录 (Sampling) 以减少高并发下的日志量
 * - [ ] 增加 Request ID 追踪 (Trace ID)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { Request, Response, NextFunction } from 'express';
import { createLogger } from '../utils/logger';

const logger = createLogger('HTTP');

/**
 * 请求日志中间件函数
 * 记录请求开始时的基本信息，并在响应结束时记录状态码和耗时
 */
export function requestLogger(req: Request, res: Response, next: NextFunction): void {
  const startTime = Date.now();

  // 记录请求进入
  logger.info({
    method: req.method,
    path: req.path,
    query: req.query,
    ip: req.ip,
    userAgent: req.get('user-agent'),
  }, 'Incoming request');

  // 监听响应结束事件
  res.on('finish', () => {
    const duration = Date.now() - startTime;

    // 记录请求完成
    logger.info({
      method: req.method,
      path: req.path,
      statusCode: res.statusCode,
      duration,
    }, 'Request completed');
  });

  next();
}
