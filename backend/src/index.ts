/**
 * @fileoverview 后端服务入口模块
 * 
 * 本文件是整个后端系统的核心入口点，负责应用程序的生命周期管理。
 * 
 * 主要职责包括：
 * 1. 服务器初始化：
 *    - 创建并配置 Express HTTP 服务器实例。
 *    - 建立 WebSocket 服务器，分别用于实时语音流传输和系统日志推送。
 * 
 * 2. 核心组件管理：
 *    - 建立与数据库的连接。
 *    - 初始化服务管理器（ServiceManager），负责协调各类 AI 服务。
 *    - 初始化会话管理器（SessionManager），维护用户状态。
 * 
 * 3. 路由与中间件配置：
 *    - 注册全局中间件（CORS、JSON 解析、日志记录等）。
 *    - 挂载各业务模块的 API 路由（认证、查询、作文、学习分析、系统管理等）。
 *    - 配置静态资源服务。
 * 
 * 4. 服务发现：
 *    - 启动 mDNS 广播服务，使局域网内的客户端能自动发现本服务。
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import express, { Express, Request, Response, NextFunction } from 'express';
import http from 'http';
import path from 'path';
import { WebSocketServer } from 'ws';
import WebSocket from 'ws';
import cors from 'cors';
import { config } from './config/env';
import { logger, logEvents } from './utils/logger';
import { errorHandler, notFoundHandler } from './middleware/error-handler';
import { requestLogger } from './middleware/request-logger';
import { Database } from './database/db';
import { SessionManager } from './managers/session-manager';
import { ServiceManager } from './managers/service-manager';
import { createAuthRoutes } from './api/routes/auth';
import { createQueryRoutes } from './api/routes/query';
import { createEssayRoutes } from './api/routes/essay';
import { createLearningRoutes } from './api/routes/learning';
import { createSystemRoutes } from './api/routes/system';
import { createAdminRoutes } from './api/routes/admin';
import { createVoiceRoutes } from './api/routes/voice';
import { createStreamHandler } from './api/handlers/stream';
import { handleSimpleAudioMessage } from './api/handlers/simple-stream';
import { startMdnsAdvertiser, MdnsAdvertiser } from './infra/mdns';

/**
 * 后端服务器类
 * 
 * 封装了 Express 应用、HTTP 服务器、WebSocket 服务器以及各核心管理器的实例。
 * 负责协调各组件的初始化顺序和启动流程。
 */
export class Server {
  private app: Express; // Express 应用实例
  private httpServer: http.Server; // Node.js 原生 HTTP 服务器
  private streamWss: WebSocketServer; // 用于语音流的 WebSocket 服务器
  private logWss: WebSocketServer; // 用于日志推送的 WebSocket 服务器
  private db!: Database; // 数据库连接实例
  private sessionManager: SessionManager; // 会话管理器
  private serviceManager!: ServiceManager; // 服务管理器
  private mdns?: MdnsAdvertiser; // mDNS 广播服务实例

  constructor() {
    this.app = express();
    this.httpServer = http.createServer(this.app);
    
    // 初始化 WebSocket 服务器
    // 使用 noServer 模式，以便在同一个 HTTP 端口上通过不同的路径（path）区分 WebSocket 服务
    // 我们将在 upgrade 事件中手动处理协议升级
    this.streamWss = new WebSocketServer({ noServer: true });
    this.logWss = new WebSocketServer({ noServer: true });
    
    // SessionManager 依赖于数据库连接，将在数据库初始化完成后实例化
    // @ts-ignore
    this.sessionManager = null; 

    // 配置基础中间件
    this.setupMiddleware();
  }

  /**
   * 配置全局中间件
   * 
   * 设置跨域资源共享 (CORS)、请求体解析 (JSON/URL-encoded) 以及请求日志记录。
   */
  private setupMiddleware(): void {
    this.app.use(cors()); // 启用 CORS 以允许前端跨域访问
    
    // 配置 JSON 请求体解析，设置较大的限制 (200mb) 以支持 Base64 图片和音频数据的上传
    this.app.use(express.json({ limit: '200mb' })); 
    this.app.use(express.urlencoded({ extended: true, limit: '200mb' }));
    
    this.app.use(requestLogger); // 挂载请求日志中间件，记录每个 HTTP 请求的详细信息
  }

  /**
   * 配置 API 路由
   */
  private setupRoutes(): void {
    // 挂载各模块路由
    this.app.use('/api/auth', createAuthRoutes(this.db));
    this.app.use('/api/query', createQueryRoutes(this.db, this.serviceManager));
    this.app.use('/api/essay', createEssayRoutes(this.db, this.serviceManager));
    this.app.use('/api/learning', createLearningRoutes(this.db, this.serviceManager));
    this.app.use('/api/system', createSystemRoutes(this.serviceManager, this.sessionManager));
    this.app.use('/api/admin', createAdminRoutes(this.db, this.serviceManager));
    this.app.use('/api/voice', createVoiceRoutes(this.serviceManager));
    
    // 静态文件服务 (前端构建产物)
    this.app.use(express.static(path.join(__dirname, '../public')));
    
    // 404 处理
    this.app.use('/api/*', notFoundHandler);
  }

  /**
   * 配置 WebSocket 服务
   * 处理 /stream (实时语音/文本流) 和 /logs (实时日志流)
   */
  private setupWebSocket(): void {
    this.httpServer.on('upgrade', (request, socket, head) => {
      const pathname = request.url ? new URL(request.url, `http://${request.headers.host}`).pathname : '';

      if (pathname === '/stream') {
        this.streamWss.handleUpgrade(request, socket, head, (ws) => {
          this.streamWss.emit('connection', ws, request);
        });
      } else if (pathname === '/logs') {
        this.logWss.handleUpgrade(request, socket, head, (ws) => {
          this.logWss.emit('connection', ws, request);
        });
      } else {
        socket.destroy();
      }
    });

    // 处理业务流连接
    this.streamWss.on('connection', (ws: WebSocket, req: any) => {
        const handler = createStreamHandler(this.serviceManager, this.sessionManager);
        handler(ws, req);
    });
    
    // 处理日志流连接
    this.logWss.on('connection', (ws: WebSocket) => {
        const listener = (log: any) => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(log));
            }
        };
        // 订阅日志事件
        logEvents.on('log', listener);
        ws.on('close', () => logEvents.off('log', listener));
    });
  }

  /**
   * 配置全局错误处理
   */
  private setupErrorHandling(): void {
    this.app.use(errorHandler);
  }

  /**
   * 初始化服务器组件
   */
  async initialize(): Promise<void> {
    try {
      // 1. 初始化数据库
      this.db = new Database();
      await this.db.initialize();
      logger.info('Database initialized');

      // 2. 初始化 SessionManager (依赖 DB)
      this.sessionManager = new SessionManager(this.db);

      // 3. 初始化服务管理器 (启动 AI 服务)
      this.serviceManager = new ServiceManager();
      await this.serviceManager.initialize();
      logger.info('Service manager initialized');

      // 4. 设置路由和 WebSocket (需要在服务初始化后)
      this.setupRoutes();
      this.setupWebSocket();
      
      // 5. 设置错误处理 (必须在最后)
      this.setupErrorHandling();

      // 6. 启动 mDNS 广播 (用于服务发现)
      this.mdns = startMdnsAdvertiser({
        port: 5555, // 软总线端口
        name: 'language-softbus',
        txt: { proto: 'zeromq', version: '1' }
      });
      logger.info('mDNS advertisement started for softbus service on port 5555');

      logger.info('Server initialized successfully');
    } catch (error) {
      logger.error({ err: error }, 'Failed to initialize server');
      throw error;
    }
  }

  /**
   * 启动 HTTP 服务器
   */
  async start(): Promise<void> {
    await this.initialize();

    // 启动后等待 3 秒预热并运行自检
    setTimeout(() => {
      logger.info('Waiting 3s before system warm-up...');
      this.serviceManager.runSelfTest().catch(err => {
        logger.error({ err }, 'System self-test failed');
      });
    }, 3000);

    // 监听服务器事件
    this.httpServer.on('listening', () => {
      const listenAddr = this.httpServer.address();
      logger.info(`✓ Server running on http://localhost:${config.port}`);
      logger.info(`✓ WebSocket running on ws://localhost:${config.port}/stream`);
      if (listenAddr && typeof listenAddr !== 'string') {
        logger.info({ address: listenAddr.address, port: listenAddr.port, family: listenAddr.family }, 'Server listening');
      }
    });

    this.httpServer.on('error', (err: any) => {
      logger.error({ code: err.code, message: err.message, port: config.port }, 'Server error');
    });

    // 启动监听
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Timeout waiting for server to start listening'));
      }, 5000);

      const onListening = () => {
        clearTimeout(timeout);
        this.httpServer.off('listening', onListening);
        this.httpServer.off('error', onError);
        logger.info('✓ Server started successfully');
        resolve();
      };

      const onError = (err: Error) => {
        clearTimeout(timeout);
        this.httpServer.off('listening', onListening);
        this.httpServer.off('error', onError);
        reject(err);
      };

      this.httpServer.once('listening', onListening);
      this.httpServer.once('error', onError);

      this.httpServer.listen(config.port, '0.0.0.0');
    });
  }

  /**
   * 优雅关闭服务器
   */
  async shutdown(): Promise<void> {
    logger.info('Shutting down server...');

    // 1. 关闭 WebSocket 连接
    this.streamWss.close();
    this.logWss.close();

    // 2. 关闭 AI 服务
    await this.serviceManager.shutdown();

    // 3. 关闭数据库连接
    await this.db.close();

    // 4. 关闭 HTTP 服务器
    this.httpServer.close(() => {
      logger.info('Server shut down');
    });

    // 5. 停止 mDNS 广播
    if (this.mdns) {
      try {
        this.mdns.stop();
        logger.info('mDNS advertisement stopped');
      } catch (e) {
        logger.warn({ err: e }, 'Failed stopping mDNS');
      }
    }
  }
}

// 主程序入口
if (require.main === module) {
  const server = new Server();

  // 全局异常捕获
  process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  });

  process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception:', error);
    try {
        const fs = require('fs');
        fs.appendFileSync('server.err.log', `[${new Date().toISOString()}] Uncaught Exception: ${error.stack || error}\n`);
    } catch (e) {}
    process.exit(1);
  });

  // 启动服务
  server.start()
    .then(() => {
      logger.info('✓ Server started successfully');
    })
    .catch(async (error) => {
      console.error('Failed to start server (Console):', error);
      try {
        logger.error('Failed to start server:', error instanceof Error ? error.message : error);
      } catch (e) {
        // ignore logger error
      }
      
      // 启动失败时的强制退出保护
      const forceExitTimer = setTimeout(() => {
        console.error('Force exiting due to shutdown timeout...');
        process.exit(1);
      }, 3000);
      forceExitTimer.unref();

      try {
        console.log('Attempting graceful shutdown...');
        await server.shutdown();
      } catch (e) {
        console.error('Error during shutdown:', e);
      } finally {
        console.log('Exiting process...');
        process.exit(1);
      }
    });

  // 信号处理 (优雅退出)
  const handleSignal = async (signal: string) => {
    console.log(`Received ${signal}, shutting down...`);
    
    const timer = setTimeout(() => {
        console.error('Force exiting due to signal shutdown timeout...');
        process.exit(1);
    }, 3000);
    timer.unref();

    try {
      await server.shutdown();
      console.log('Shutdown complete');
      process.exit(0);
    } catch (err) {
      console.error('Error during shutdown:', err);
      process.exit(1);
    }
  };

  // Windows 兼容性
  if (process.platform === 'win32') {
    const rl = require('readline').createInterface({
      input: process.stdin,
      output: process.stdout
    });

    rl.on('SIGINT', () => {
      process.emit('SIGINT');
    });
  }

  process.on('SIGTERM', () => handleSignal('SIGTERM'));
  process.on('SIGINT', () => handleSignal('SIGINT'));
}
