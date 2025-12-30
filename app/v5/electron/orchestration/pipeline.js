/**
 * Pipeline - 多步骤处理管道
 * 支持串联和并联执行
 */
import log from 'electron-log';
/**
 * 管道执行引擎
 */
export class Pipeline {
    config;
    orchestrator; // ServiceOrchestrator 引用
    constructor(config, orchestrator) {
        this.config = config;
        this.orchestrator = orchestrator;
    }
    /**
     * 执行管道
     */
    async execute(context) {
        const pipelineStartTime = Date.now();
        try {
            log.info(`[${context.requestId}] Executing pipeline: ${this.config.name}`);
            if (this.config.parallel) {
                await this.executeParallel(context);
            }
            else {
                await this.executeSequential(context);
            }
            const duration = Date.now() - pipelineStartTime;
            log.info(`[${context.requestId}] Pipeline ${this.config.name} completed (${duration}ms)`);
            return {
                success: true,
                data: this.collectResults(context),
                duration,
                traceId: context.traceId,
            };
        }
        catch (error) {
            const duration = Date.now() - pipelineStartTime;
            const errMsg = error instanceof Error ? error.message : String(error);
            log.error(`[${context.requestId}] Pipeline ${this.config.name} failed: ${errMsg}`);
            return {
                success: false,
                error: errMsg,
                duration,
                traceId: context.traceId,
            };
        }
    }
    /**
     * 串联执行步骤
     */
    async executeSequential(context) {
        for (const step of this.config.steps) {
            try {
                // 检查执行条件
                if (step.condition && !step.condition(context)) {
                    log.debug(`[${context.requestId}] Skipping step ${step.name} (condition not met)`);
                    continue;
                }
                await this.executeStep(step, context);
            }
            catch (error) {
                if (!step.continueOnError) {
                    throw error;
                }
                log.warn(`[${context.requestId}] Step ${step.name} failed but continuing:`, error);
            }
        }
    }
    /**
     * 并联执行步骤
     */
    async executeParallel(context) {
        const promises = [];
        for (const step of this.config.steps) {
            // 检查执行条件
            if (step.condition && !step.condition(context)) {
                continue;
            }
            promises.push(this.executeStep(step, context).catch(error => {
                if (!step.continueOnError) {
                    throw error;
                }
                log.warn(`[${context.requestId}] Step ${step.name} failed but continuing:`, error);
            }));
        }
        await Promise.all(promises);
    }
    /**
     * 执行单个步骤
     */
    async executeStep(step, context) {
        const stepStartTime = Date.now();
        try {
            log.info(`[${context.requestId}] Executing step: ${step.name}`);
            // 构建参数
            let params = context.payload;
            if (step.paramMap) {
                params = this.mapParameters(context.payload, step.paramMap);
            }
            // 获取服务并调用
            const service = this.orchestrator.services?.get(step.serviceName);
            if (!service) {
                throw new Error(`Service not found: ${step.serviceName}`);
            }
            const timeout = step.timeout || this.config.timeout || 30000;
            const startTime = Date.now();
            let result;
            try {
                result = await service.invoke(step.name, params, timeout);
            }
            catch (error) {
                if (step.errorHandler) {
                    result = await step.errorHandler(error);
                }
                else {
                    throw error;
                }
            }
            // 映射结果
            if (step.resultMap && result) {
                result = this.mapResult(result, step.resultMap);
            }
            // 保存中间结果
            context.intermediateResults.set(step.name, {
                result,
                duration: Date.now() - startTime,
                timestamp: Date.now(),
            });
            const duration = Date.now() - stepStartTime;
            log.debug(`[${context.requestId}] Step ${step.name} completed (${duration}ms)`);
        }
        catch (error) {
            const duration = Date.now() - stepStartTime;
            log.error(`[${context.requestId}] Step ${step.name} failed (${duration}ms):`, error);
            if (step.errorHandler) {
                try {
                    const fallbackResult = await step.errorHandler(error);
                    context.intermediateResults.set(step.name, {
                        result: fallbackResult,
                        duration,
                        error: true,
                        timestamp: Date.now(),
                    });
                    if (step.continueOnError) {
                        return;
                    }
                }
                catch (fallbackError) {
                    throw fallbackError;
                }
            }
            throw error;
        }
    }
    /**
     * 参数映射
     */
    mapParameters(payload, paramMap) {
        const params = {};
        for (const [key, paramName] of Object.entries(paramMap)) {
            params[paramName] = payload[key];
        }
        return params;
    }
    /**
     * 结果映射
     */
    mapResult(result, resultMap) {
        const mapped = {};
        for (const [responseKey, outputKey] of Object.entries(resultMap)) {
            mapped[outputKey] = result[responseKey];
        }
        return mapped;
    }
    /**
     * 收集所有中间结果
     */
    collectResults(context) {
        const results = {};
        for (const [stepName, stepResult] of context.intermediateResults) {
            results[stepName] = stepResult.result;
        }
        return results;
    }
}
//# sourceMappingURL=pipeline.js.map