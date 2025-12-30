/**
 * Service Orchestrator - 核心编排引擎
 * 负责消息路由、服务激活、管道执行
 */
import { EventEmitter } from 'node:events';
import { ServiceInstance, ProcessingResult, OrchestratorConfig, Metrics } from './types.js';
/**
 * 服务编排器 - 主控制器
 */
export declare class ServiceOrchestrator extends EventEmitter {
    private config;
    private services;
    private pipelines;
    private routingRules;
    private metrics;
    private processingQueue;
    private resultCache;
    constructor(config: OrchestratorConfig);
    /**
     * 初始化服务
     */
    private initializeServices;
    /**
     * 初始化消息路由
     */
    private initializeRouting;
    /**
     * 初始化管道
     */
    private initializePipelines;
    /**
     * 启动编排器
     */
    start(): Promise<void>;
    /**
     * 停止编排器
     */
    stop(): Promise<void>;
    /**
     * 处理 Softbus 消息
     */
    handleMessage(topic: string, payload: any, contentType?: string): Promise<ProcessingResult>;
    /**
     * 获取服务状态
     */
    getServiceStates(): Record<string, ServiceInstance>;
    /**
     * 获取指标
     */
    getMetrics(): Metrics;
    /**
     * 获取管道列表
     */
    getPipelines(): string[];
    /**
     * 执行指定管道
     */
    executePipeline(pipelineName: string, payload: any): Promise<ProcessingResult>;
    /**
     * 预热模型
     */
    private warmupModels;
    /**
     * 匹配路由规则
     */
    private matchRoute;
    /**
     * 主题模式匹配
     * 支持: * (单层通配符) 和 # (多层通配符)
     */
    private matchPattern;
    /**
     * 生成缓存键
     */
    private generateCacheKey;
    /**
     * 创建处理结果
     */
    private createResult;
    /**
     * 更新指标
     */
    private updateMetrics;
    /**
     * 清理资源
     */
    cleanup(): Promise<void>;
}
export { ServiceOrchestrator as Orchestrator };
//# sourceMappingURL=orchestrator.d.ts.map