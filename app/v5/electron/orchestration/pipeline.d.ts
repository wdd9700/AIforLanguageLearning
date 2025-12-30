/**
 * Pipeline - 多步骤处理管道
 * 支持串联和并联执行
 */
import { PipelineConfig, ProcessingContext, ProcessingResult } from './types.js';
/**
 * 管道执行引擎
 */
export declare class Pipeline {
    private config;
    private orchestrator;
    constructor(config: PipelineConfig, orchestrator: any);
    /**
     * 执行管道
     */
    execute(context: ProcessingContext): Promise<ProcessingResult>;
    /**
     * 串联执行步骤
     */
    private executeSequential;
    /**
     * 并联执行步骤
     */
    private executeParallel;
    /**
     * 执行单个步骤
     */
    private executeStep;
    /**
     * 参数映射
     */
    private mapParameters;
    /**
     * 结果映射
     */
    private mapResult;
    /**
     * 收集所有中间结果
     */
    private collectResults;
}
//# sourceMappingURL=pipeline.d.ts.map