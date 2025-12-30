/**
 * @fileoverview 基础服务抽象类 (Base Service)
 * 
 * 定义了所有后端服务的通用接口和状态管理逻辑。
 * 所有具体的服务实现 (LLM, ASR, TTS, OCR) 都应继承此类。
 * 
 * 主要功能：
 * 1. 状态管理：维护服务的运行状态 (running/stopped/error) 和健康指标
 * 2. 生命周期接口：定义 initialize, shutdown, healthCheck 等抽象方法
 * 3. 事件通知：状态变更时触发 'statusChange' 事件
 * 4. 统一日志：为每个服务实例创建独立的 Logger
 * 
 * 待改进项：
 * - [ ] 增加统一的性能监控指标 (Metrics) 收集接口
 * - [ ] 实现分布式追踪 (Tracing) 上下文传递
 * - [ ] 增强错误重试和熔断机制的基类支持
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { createLogger } from '../utils/logger';
import { EventEmitter } from 'events';

export interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped' | 'error' | 'initializing';
  lastCheck: number;
  errorCount: number;
  message?: string;
  details?: any;
}

export abstract class BaseService extends EventEmitter {
  protected name: string;
  protected logger: any;
  protected status: ServiceStatus;

  constructor(name: string) {
    super();
    this.name = name;
    this.logger = createLogger(name);
    this.status = {
      name,
      status: 'stopped',
      lastCheck: Date.now(),
      errorCount: 0
    };
  }

  /**
   * 初始化服务
   * 子类应实现具体的初始化逻辑，如建立连接、加载模型等。
   */
  abstract initialize(): Promise<void>;

  /**
   * 关闭服务
   * 子类应实现具体的资源释放逻辑。
   */
  abstract shutdown(): Promise<void>;

  /**
   * 执行健康检查
   * 子类应实现具体的检查逻辑，返回 true 表示健康，false 表示异常。
   */
  abstract healthCheck(): Promise<boolean>;

  /**
   * 获取当前服务状态
   * 返回状态对象的副本，防止外部直接修改。
   */
  public getStatus(): ServiceStatus {
    return { ...this.status };
  }

  /**
   * 更新服务状态
   * 自动更新最后检查时间，并触发 'statusChange' 事件。
   * @param status 新的状态
   * @param message 状态描述信息
   * @param details 详细的状态数据
   */
  protected updateStatus(status: ServiceStatus['status'], message?: string, details?: any) {
    this.status.status = status;
    this.status.lastCheck = Date.now();
    if (message) this.status.message = message;
    if (details) this.status.details = details;
    
    if (status === 'running') {
      this.status.errorCount = 0;
    } else if (status === 'error') {
      this.status.errorCount++;
    }

    this.emit('statusChange', this.status);
    this.logger.debug({ status, message }, 'Service status updated');
  }
}
