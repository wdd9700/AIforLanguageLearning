/**
 * @fileoverview 日志工具模块 (Logger)
 * 
 * 基于 Pino 的高性能日志系统，支持控制台输出和文件持久化。
 * 提供日志事件钩子，便于实时监控和 WebSocket 推送。
 * 
 * 主要功能：
 * 1. 多目标输出：同时支持控制台 (Pretty Print) 和文件 (JSON)
 * 2. 事件钩子：通过 EventEmitter 广播日志事件，供上层业务订阅 (如推送到前端)
 * 3. 模块化实例：支持创建带有 module 标签的子日志器
 * 
 * 待改进项：
 * - [ ] 集成日志轮转 (Log Rotation) 防止单个日志文件过大
 * - [ ] 支持运行时动态调整日志级别
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import pino from 'pino';
import path from 'path';
import fs from 'fs';
import { EventEmitter } from 'events';
import { config } from '../config/env';

// 导出日志事件发射器，用于实时日志流
export const logEvents = new EventEmitter();

// 确保日志目录存在
const logDir = path.dirname(config.log.file);
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

// 创建 Pino 日志实例
export const logger = pino({
  level: config.log.level,
  hooks: {
    // 拦截日志方法调用，触发事件
    logMethod(inputArgs, method, level) {
      // inputArgs 是 [obj, msg, ...args] 或 [msg, ...args]
      // level 是日志级别数值 (30=info, 40=warn, 50=error)
      
      let logData: any = {
        timestamp: Date.now(),
        level: level,
        levelLabel: logger.levels.labels[level],
      };

      // 解析参数
      if (typeof inputArgs[0] === 'string') {
        logData.msg = inputArgs[0];
        if (inputArgs.length > 1) logData.args = inputArgs.slice(1);
      } else if (typeof inputArgs[0] === 'object') {
        logData = { ...logData, ...inputArgs[0] };
        if (inputArgs[1]) logData.msg = inputArgs[1];
      }

      // 发射日志事件，供 WebSocket 广播使用
      logEvents.emit('log', logData);

      return method.apply(this, inputArgs as [string, ...any[]]);
    },
  },
  transport: {
    targets: [
      // 控制台输出 (开发环境友好格式)
      {
        target: 'pino-pretty',
        level: config.log.level,
        options: {
          colorize: true,
          translateTime: 'yyyy-mm-dd HH:MM:ss',
          ignore: 'pid,hostname',
        },
      },
      // 文件输出 (持久化存储)
      {
        target: 'pino/file',
        level: 'info',
        options: {
          destination: config.log.file,
          mkdir: true,
        },
      },
    ],
  },
});

/**
 * 创建子日志器
 * 为特定模块创建带有模块名称标记的日志实例
 * 
 * @param name 模块名称
 * @returns 子日志实例
 */
export function createLogger(name: string) {
  return logger.child({ module: name });
}

// 兼容旧代码的 Logger 类导出
export class Logger {
  private pinoLogger: pino.Logger;

  constructor(name: string) {
    this.pinoLogger = createLogger(name);
  }

  info(msg: string, ...args: any[]): void;
  info(obj: object, msg?: string, ...args: any[]): void;
  info(arg1: any, arg2?: any, ...args: any[]): void {
    this.pinoLogger.info(arg1, arg2, ...args);
  }

  error(msg: string, ...args: any[]): void;
  error(obj: object, msg?: string, ...args: any[]): void;
  error(arg1: any, arg2?: any, ...args: any[]): void {
    this.pinoLogger.error(arg1, arg2, ...args);
  }

  warn(msg: string, ...args: any[]): void;
  warn(obj: object, msg?: string, ...args: any[]): void;
  warn(arg1: any, arg2?: any, ...args: any[]): void {
    this.pinoLogger.warn(arg1, arg2, ...args);
  }

  debug(msg: string, ...args: any[]): void;
  debug(obj: object, msg?: string, ...args: any[]): void;
  debug(arg1: any, arg2?: any, ...args: any[]): void {
    this.pinoLogger.debug(arg1, arg2, ...args);
  }
}
