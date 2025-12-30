/**
 * @fileoverview 后端编排器 (Orchestrator)
 * 
 * 核心服务调度引擎，负责协调系统内的所有服务和消息流转。
 * 实现了基于 Topic 的消息路由、服务生命周期管理、会话鉴权以及业务流水线执行。
 * 
 * 主要功能：
 * 1. 消息路由 (Routing)：根据 Topic 将消息分发给单个服务或流水线
 * 2. 服务管理 (Service Mgmt)：服务的激活、预热、调用和状态监控
 * 3. 会话管理 (Session Mgmt)：会话创建、验证、心跳维护和用户绑定
 * 4. 流水线执行 (Pipeline)：支持多步骤服务调用、条件执行和参数映射
 * 5. 错误处理：统一的异常捕获和错误响应格式
 * 
 * 架构说明：
 * 目前 Orchestrator 使用了本地定义的 ServiceManager (./service-manager) 而非全局的 ServiceManager。
 * 这是一个已知的技术债务，未来需要统一接口并注入全局 ServiceManager 实例。
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { Message, ServiceConfig, OrchestratorConfig, TOPICS } from '../shared/types';
import { ServiceManager } from '../managers/service-manager';
import { SessionManager } from '../managers/session-manager';
import { MessageProcessor } from './message-processor';
import { Logger } from '../utils/logger';

export class Orchestrator {
  private config: OrchestratorConfig;
  private serviceManager: ServiceManager;
  private sessionManager: SessionManager;
  private messageProcessor: MessageProcessor;
  private logger: Logger;

  constructor(config: OrchestratorConfig, serviceManager?: ServiceManager, sessionManager?: SessionManager) {
    this.config = config;
    this.logger = new Logger('Orchestrator');
    // 使用注入的全局管理器，或者创建新的（注意：创建新的会导致状态隔离，建议注入）
    this.serviceManager = serviceManager || new ServiceManager();
    this.sessionManager = sessionManager || new SessionManager();
    this.messageProcessor = new MessageProcessor();
  }

  /**
   * 初始化编排器
   * 启动核心服务并进行预热
   */
  async initialize(): Promise<void> {
    this.logger.info('Initializing orchestrator...');

    // 启动核心服务（带 warmup 的服务）
    for (const [name, config] of Object.entries(this.config.services)) {
      if (config.warmup?.enabled && config.warmup.trigger === 'startup') {
        try {
          await this.serviceManager.activate(name);
          this.logger.info(`Service ${name} warmed up`);
        } catch (error) {
          this.logger.error(`Failed to warmup service ${name}:`, error);
        }
      }
    }

    this.logger.info('Orchestrator initialized');
  }

  /**
   * 处理来自客户端的消息
   * 包含会话验证、心跳更新和路由分发
   */
  async handleMessage(message: Message): Promise<any> {
    const requestId = message.metadata.requestId;

    try {
      this.logger.debug(`Processing message ${requestId} on topic ${message.topic}`);

      // 1. 验证会话
      const session = await this.sessionManager.getSession(message.sessionId);
      if (!session) {
        throw new Error('Invalid session');
      }

      // 2. 更新心跳
      await this.sessionManager.updateHeartbeat(message.sessionId);

      // 3. 根据主题路由
      const response = await this.route(message, session);

      this.logger.debug(`Message ${requestId} processed successfully`);

      return {
        ok: true,
        code: 0,
        data: response,
      };
    } catch (error: any) {
      this.logger.error(`Error processing message ${requestId}:`, error);

      return {
        ok: false,
        code: error.code || 500,
        message: error.message,
        error: {
          code: error.errorCode || 'INTERNAL_ERROR',
          message: error.message,
        },
      };
    }
  }

  /**
   * 消息路由
   * 根据 Topic 将消息分发给单个服务或流水线
   */
  private async route(message: Message, session: any): Promise<any> {
    const { topic, payload, metadata } = message;

    // 查找匹配的路由规则
    const routeRule = this.findRoute(topic);
    if (!routeRule) {
      throw new Error(`No route found for topic: ${topic}`);
    }

    // 流水线处理 (Pipeline)
    if (routeRule.pipeline && routeRule.pipeline.length > 0) {
      return this.executePipeline(routeRule.pipeline, payload.data, metadata);
    }

    // 单服务处理
    if (routeRule.service) {
      const service = await this.serviceManager.activate(routeRule.service);
      return service.invoke(payload.data, {
        timeout: routeRule.timeout || metadata.timeout,
        retries: routeRule.retry || 0,
        userId: session.userId,
        requestId: metadata.requestId,
      });
    }

    throw new Error('Invalid route configuration');
  }

  /**
   * 查找匹配的路由规则
   * 支持精确匹配和通配符匹配
   */
  private findRoute(topic: string) {
    // 精确匹配
    if (this.config.routes[topic]) {
      return this.config.routes[topic];
    }

    // 通配符匹配
    for (const [pattern, rule] of Object.entries(this.config.routes)) {
      if (this.matchPattern(pattern, topic)) {
        return rule;
      }
    }

    return null;
  }

  /**
   * 主题模式匹配
   */
  private matchPattern(pattern: string, topic: string): boolean {
    // svc/* 匹配所有 svc/ 开头的主题
    if (pattern === 'svc/*') {
      return topic.startsWith('svc/');
    }

    // 精确匹配
    return pattern === topic;
  }

  /**
   * 执行流水线
   * 按顺序调用多个服务，支持条件判断和参数映射
   */
  private async executePipeline(steps: any[], input: any, metadata: any): Promise<any> {
    let result = input;
    const context: Record<string, any> = { input };

    for (const step of steps) {
      // 条件检查
      if (step.condition && !step.condition(context)) {
        this.logger.debug(`Pipeline step skipped due to condition: ${step.service}`);
        continue;
      }

      // 激活服务
      const service = await this.serviceManager.activate(step.service);

      // 参数映射
      const inputData = step.inputField ? result[step.inputField] : result;

      // 调用服务
      try {
        result = await service.invoke(inputData, {
          timeout: metadata.timeout,
          userId: metadata.userId,
          requestId: metadata.requestId,
        });
      } catch (error: any) {
        // 错误处理
        if (step.errorHandler === 'continue') {
          this.logger.warn(`Service ${step.service} failed, continuing: ${error.message}`);
          continue;
        }
        throw error;
      }

      // 结果映射
      if (step.outputField) {
        context[step.outputField] = result;
        result = context;
      } else {
        context.result = result;
      }
    }

    return result;
  }

  /**
   * 创建会话
   */
  async createSession(peerId: string, capabilities: any): Promise<string> {
    const sessionId = await this.sessionManager.createSession(peerId, capabilities);
    this.logger.info(`Session created: ${sessionId}`);
    return sessionId;
  }

  /**
   * 绑定用户到会话
   */
  async bindUser(sessionId: string, userId: string): Promise<void> {
    await this.sessionManager.bindUser(sessionId, userId);
    this.logger.info(`User ${userId} bound to session ${sessionId}`);
  }

  /**
   * 获取服务状态
   */
  async getServiceStatus(): Promise<Record<string, any>> {
    return this.serviceManager.getStatus();
  }

  /**
   * 清理资源
   */
  async cleanup(): Promise<void> {
    this.logger.info('Cleaning up orchestrator...');
    await this.serviceManager.shutdown();
    await this.sessionManager.cleanup();
    this.logger.info('Orchestrator cleaned up');
  }
}
