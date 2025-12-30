/**
 * Service Orchestrator - 核心编排引擎
 * 负责消息路由、服务激活、管道执行
 */
import log from 'electron-log';
import { EventEmitter } from 'node:events';
import { createService } from './service.js';
import { Pipeline } from './pipeline.js';
/**
 * 服务编排器 - 主控制器
 */
export class ServiceOrchestrator extends EventEmitter {
    config;
    services = new Map();
    pipelines = new Map();
    routingRules = [];
    metrics = {
        requestCount: 0,
        successCount: 0,
        failureCount: 0,
        avgResponseTime: 0,
        maxResponseTime: 0,
        minResponseTime: Infinity,
        currentConcurrency: 0,
    };
    processingQueue = new Set();
    resultCache = new Map();
    constructor(config) {
        super();
        this.config = config;
        this.initializeServices();
        this.initializeRouting();
        this.initializePipelines();
    }
    /**
     * 初始化服务
     */
    initializeServices() {
        for (const [name, config] of Object.entries(this.config.services)) {
            try {
                const service = createService(config);
                this.services.set(name, service);
                log.info(`Service registered: ${name}`);
            }
            catch (error) {
                log.error(`Failed to register service ${name}:`, error);
            }
        }
    }
    /**
     * 初始化消息路由
     */
    initializeRouting() {
        this.routingRules = [...(this.config.routes || [])];
        // 按优先级排序
        this.routingRules.sort((a, b) => (b.priority || 0) - (a.priority || 0));
        log.info(`Routing rules initialized: ${this.routingRules.length} rules`);
    }
    /**
     * 初始化管道
     */
    initializePipelines() {
        if (!this.config.pipelines)
            return;
        for (const [name, config] of Object.entries(this.config.pipelines)) {
            try {
                const pipeline = new Pipeline(config, this);
                this.pipelines.set(name, pipeline);
                log.info(`Pipeline registered: ${name}`);
            }
            catch (error) {
                log.error(`Failed to register pipeline ${name}:`, error);
            }
        }
    }
    /**
     * 启动编排器
     */
    async start() {
        log.info('Starting ServiceOrchestrator...');
        try {
            // 启动所有服务（按优先级）
            const services = Array.from(this.services.values()).sort((a, b) => {
                const configA = this.config.services[a.getName()];
                const configB = this.config.services[b.getName()];
                return (configB?.priority || 0) - (configA?.priority || 0);
            });
            for (const service of services) {
                try {
                    await service.start();
                }
                catch (error) {
                    log.warn(`Failed to start service ${service.getName()}:`, error);
                }
            }
            // 执行预热
            await this.warmupModels();
            log.info('ServiceOrchestrator started successfully');
            this.emit('started');
        }
        catch (error) {
            log.error('Failed to start ServiceOrchestrator:', error);
            throw error;
        }
    }
    /**
     * 停止编排器
     */
    async stop() {
        log.info('Stopping ServiceOrchestrator...');
        try {
            for (const service of this.services.values()) {
                try {
                    await service.stop();
                }
                catch (error) {
                    log.warn(`Failed to stop service:`, error);
                }
            }
            this.resultCache.clear();
            log.info('ServiceOrchestrator stopped');
            this.emit('stopped');
        }
        catch (error) {
            log.error('Error stopping ServiceOrchestrator:', error);
            throw error;
        }
    }
    /**
     * 处理 Softbus 消息
     */
    async handleMessage(topic, payload, contentType = 'application/octet-stream') {
        const requestId = `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const traceId = `trace-${Date.now()}`;
        const context = {
            requestId,
            traceId,
            payload,
            headers: { 'content-type': contentType },
            startTime: Date.now(),
            intermediateResults: new Map(),
        };
        log.info(`[${requestId}] Processing message: topic=${topic}, contentType=${contentType}`);
        this.metrics.requestCount++;
        this.metrics.currentConcurrency++;
        this.processingQueue.add(requestId);
        try {
            // 查询缓存
            const cacheKey = this.generateCacheKey(topic, payload);
            if (this.config.cacheConfig?.enabled && this.resultCache.has(cacheKey)) {
                const cached = this.resultCache.get(cacheKey);
                if (Date.now() - cached.timestamp < (this.config.cacheConfig.ttl || 60000)) {
                    log.info(`[${requestId}] Cache hit for ${topic}`);
                    return this.createResult(true, cached.data, context);
                }
            }
            // 匹配路由规则
            const rule = this.matchRoute(topic);
            if (!rule) {
                throw new Error(`No routing rule matched for topic: ${topic}`);
            }
            log.info(`[${requestId}] Matched routing rule: ${rule.serviceName}`);
            // 查找服务或管道
            let result;
            if (this.pipelines.has(rule.serviceName)) {
                const pipeline = this.pipelines.get(rule.serviceName);
                result = await pipeline.execute(context);
            }
            else if (this.services.has(rule.serviceName)) {
                const service = this.services.get(rule.serviceName);
                result = await service.invoke(topic, payload, rule.timeout);
            }
            else {
                throw new Error(`Service not found: ${rule.serviceName}`);
            }
            // 应用后处理
            if (rule.postprocess) {
                result = await rule.postprocess(result);
            }
            // 缓存结果
            if (this.config.cacheConfig?.enabled && cacheKey) {
                this.resultCache.set(cacheKey, { data: result, timestamp: Date.now() });
            }
            this.metrics.successCount++;
            return this.createResult(true, result, context);
        }
        catch (error) {
            this.metrics.failureCount++;
            const errMsg = error instanceof Error ? error.message : String(error);
            log.error(`[${requestId}] Processing failed: ${errMsg}`);
            return this.createResult(false, undefined, context, errMsg);
        }
        finally {
            this.processingQueue.delete(requestId);
            this.metrics.currentConcurrency--;
            const duration = Date.now() - context.startTime;
            this.updateMetrics(duration);
        }
    }
    /**
     * 获取服务状态
     */
    getServiceStates() {
        const states = {};
        for (const [name, service] of this.services) {
            states[name] = service.getInstance();
        }
        return states;
    }
    /**
     * 获取指标
     */
    getMetrics() {
        return { ...this.metrics };
    }
    /**
     * 获取管道列表
     */
    getPipelines() {
        return Array.from(this.pipelines.keys());
    }
    /**
     * 执行指定管道
     */
    async executePipeline(pipelineName, payload) {
        const pipeline = this.pipelines.get(pipelineName);
        if (!pipeline) {
            throw new Error(`Pipeline not found: ${pipelineName}`);
        }
        const context = {
            requestId: `req-${Date.now()}`,
            traceId: `trace-${Date.now()}`,
            payload,
            startTime: Date.now(),
            intermediateResults: new Map(),
        };
        return await pipeline.execute(context);
    }
    /**
     * 预热模型
     */
    async warmupModels() {
        if (!this.config.warmupConfigs || this.config.warmupConfigs.length === 0) {
            return;
        }
        log.info('Starting model warmup...');
        const warmups = [...this.config.warmupConfigs].sort((a, b) => (b.priority || 0) - (a.priority || 0));
        for (const config of warmups) {
            try {
                const service = this.services.get(config.serviceName);
                if (!service) {
                    log.warn(`Service not found for warmup: ${config.serviceName}`);
                    continue;
                }
                log.info(`Warming up ${config.serviceName}/${config.modelId}...`);
                const startTime = Date.now();
                await service.invoke('warmup', config.input, config.timeout);
                const duration = Date.now() - startTime;
                log.info(`Warmup completed for ${config.serviceName}/${config.modelId} (${duration}ms)`);
            }
            catch (error) {
                log.warn(`Warmup failed for ${config.serviceName}:`, error);
            }
        }
        log.info('Model warmup completed');
    }
    /**
     * 匹配路由规则
     */
    matchRoute(topic) {
        for (const rule of this.routingRules) {
            if (this.matchPattern(topic, rule.pattern)) {
                return rule;
            }
        }
        return undefined;
    }
    /**
     * 主题模式匹配
     * 支持: * (单层通配符) 和 # (多层通配符)
     */
    matchPattern(topic, pattern) {
        const topicParts = topic.split('/');
        const patternParts = pattern.split('/');
        for (let i = 0; i < patternParts.length; i++) {
            const part = patternParts[i];
            if (part === '#') {
                // 多层通配符，匹配剩余所有部分
                return true;
            }
            if (part === '*') {
                // 单层通配符
                if (i >= topicParts.length) {
                    return false;
                }
                continue;
            }
            // 精确匹配
            if (topicParts[i] !== part) {
                return false;
            }
        }
        return topicParts.length === patternParts.length;
    }
    /**
     * 生成缓存键
     */
    generateCacheKey(topic, payload) {
        const keyGen = this.config.cacheConfig?.keyGenerator;
        if (keyGen) {
            return keyGen(topic, payload);
        }
        // 简单的缓存键生成
        return `${topic}:${JSON.stringify(payload).substring(0, 100)}`;
    }
    /**
     * 创建处理结果
     */
    createResult(success, data, context, error) {
        return {
            success,
            data,
            error,
            duration: Date.now() - context.startTime,
            traceId: context.traceId,
        };
    }
    /**
     * 更新指标
     */
    updateMetrics(duration) {
        const total = this.metrics.requestCount;
        this.metrics.avgResponseTime = (this.metrics.avgResponseTime * (total - 1) + duration) / total;
        this.metrics.maxResponseTime = Math.max(this.metrics.maxResponseTime, duration);
        this.metrics.minResponseTime = Math.min(this.metrics.minResponseTime, duration);
    }
    /**
     * 清理资源
     */
    async cleanup() {
        await this.stop();
        for (const service of this.services.values()) {
            await service.cleanup();
        }
        this.services.clear();
        this.pipelines.clear();
    }
}
export { ServiceOrchestrator as Orchestrator };
//# sourceMappingURL=orchestrator.js.map