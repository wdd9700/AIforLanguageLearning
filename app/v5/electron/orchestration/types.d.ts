/**
 * Service Orchestration Framework - Type Definitions
 * 定义服务编排、管道、服务配置等核心类型
 */
/**
 * 服务状态枚举
 */
export declare enum ServiceStatus {
    /** 已停止 */
    STOPPED = "stopped",
    /** 启动中 */
    STARTING = "starting",
    /** 运行中 */
    RUNNING = "running",
    /** 预热中 */
    WARMING = "warming",
    /** 错误 */
    ERROR = "error",
    /** 已关闭 */
    SHUTDOWN = "shutdown"
}
/**
 * 服务配置
 */
export interface ServiceConfig {
    /** 服务名称 (ocr, asr, tts, llm) */
    name: string;
    /** 服务类型 (process 或 http) */
    type: 'process' | 'http';
    /** 进程命令（如 'python -m surya'） */
    command?: string;
    /** 工作目录 */
    cwd?: string;
    /** 环境变量 */
    env?: Record<string, string>;
    /** HTTP 端点 */
    endpoint?: string;
    /** 启动超时（毫秒） */
    startTimeout?: number;
    /** 健康检查端点 */
    healthCheck?: string;
    /** 健康检查间隔（毫秒） */
    healthCheckInterval?: number;
    /** 自动重启次数 */
    autoRestartCount?: number;
    /** 自动重启延迟（毫秒） */
    autoRestartDelay?: number;
    /** 预热脚本（可选） */
    warmupScript?: string;
    /** 优先级（0-100，越高越优先加载） */
    priority?: number;
    /** 额外配置选项 (如 modelName 等) */
    options?: Record<string, any>;
}
/**
 * 服务实例状态
 */
export interface ServiceInstance {
    /** 服务名称 */
    name: string;
    /** 当前状态 */
    status: ServiceStatus;
    /** 进程 ID（进程服务） */
    pid?: number;
    /** 启动时间 */
    startedAt?: number;
    /** 最后心跳时间 */
    lastHeartbeat?: number;
    /** 错误信息 */
    error?: string;
    /** 重启次数 */
    restartCount: number;
    /** 内存占用（MB） */
    memoryUsage?: number;
    /** CPU 使用率（%） */
    cpuUsage?: number;
}
/**
 * 消息路由规则
 */
export interface RoutingRule {
    /** 主题匹配模式 (支持通配符: svc/ocr, svc/*, svc/#) */
    pattern: string;
    /** 服务名称 */
    serviceName: string;
    /** 优先级（0-100） */
    priority?: number;
    /** 超时（毫秒） */
    timeout?: number;
    /** 是否为流处理 */
    isStream?: boolean;
    /** 预处理函数 */
    preprocess?: (data: any) => Promise<any>;
    /** 后处理函数 */
    postprocess?: (result: any) => Promise<any>;
}
/**
 * 处理步骤
 */
export interface PipelineStep {
    /** 步骤名称 */
    name: string;
    /** 执行的服务 */
    serviceName: string;
    /** 参数映射 (字段名 -> 参数名) */
    paramMap?: Record<string, string>;
    /** 结果映射 (响应字段 -> 步骤输出字段) */
    resultMap?: Record<string, string>;
    /** 条件判断（是否执行此步骤） */
    condition?: (context: any) => boolean;
    /** 重试次数 */
    retries?: number;
    /** 超时（毫秒） */
    timeout?: number;
    /** 是否允许失败（继续执行后续步骤） */
    continueOnError?: boolean;
    /** 错误处理函数 */
    errorHandler?: (error: Error) => Promise<any>;
}
/**
 * 管道配置（用于复杂多步处理）
 */
export interface PipelineConfig {
    /** 管道名称 */
    name: string;
    /** 处理步骤 */
    steps: PipelineStep[];
    /** 是否并行执行（同优先级步骤） */
    parallel?: boolean;
    /** 超时（毫秒） */
    timeout?: number;
}
/**
 * 处理上下文
 */
export interface ProcessingContext {
    /** 请求 ID（用于追踪） */
    requestId: string;
    /** 追踪 ID */
    traceId: string;
    /** 消息内容 */
    payload: any;
    /** 消息头信息 */
    headers?: Record<string, string>;
    /** 处理开始时间 */
    startTime: number;
    /** 中间结果存储 */
    intermediateResults: Map<string, any>;
    /** 元数据 */
    metadata?: Record<string, any>;
}
/**
 * 处理结果
 */
export interface ProcessingResult {
    /** 是否成功 */
    success: boolean;
    /** 结果数据 */
    data?: any;
    /** 错误信息 */
    error?: string;
    /** 错误代码 */
    errorCode?: number;
    /** 处理耗时（毫秒） */
    duration: number;
    /** 追踪 ID */
    traceId?: string;
    /** 服务执行详情 */
    serviceDetails?: {
        [serviceName: string]: {
            status: 'success' | 'failed' | 'skipped';
            duration: number;
            error?: string;
        };
    };
}
/**
 * 模型预热配置
 */
export interface WarmupConfig {
    /** 模型名称或 ID */
    modelId: string;
    /** 服务名称 */
    serviceName: string;
    /** 预热输入（示例数据） */
    input: any;
    /** 预热优先级（0-100，越高越先执行） */
    priority?: number;
    /** 预热超时（毫秒） */
    timeout?: number;
}
/**
 * 缓存配置
 */
export interface CacheConfig {
    /** 是否启用缓存 */
    enabled: boolean;
    /** 缓存有效期（毫秒） */
    ttl?: number;
    /** 最大缓存项数 */
    maxSize?: number;
    /** 缓存键生成函数 */
    keyGenerator?: (serviceName: string, params: any) => string;
}
/**
 * 编排器配置
 */
export interface OrchestratorConfig {
    /** 服务配置映射 */
    services: Record<string, ServiceConfig>;
    /** 消息路由规则 */
    routes: RoutingRule[];
    /** 管道定义 */
    pipelines?: Record<string, PipelineConfig>;
    /** 预热配置 */
    warmupConfigs?: WarmupConfig[];
    /** 缓存配置 */
    cacheConfig?: CacheConfig;
    /** 全局超时（毫秒） */
    globalTimeout?: number;
    /** 健康检查间隔（毫秒） */
    healthCheckInterval?: number;
    /** 最大并发处理数 */
    maxConcurrency?: number;
    /** 是否启用分布式追踪 */
    enableTracing?: boolean;
    /** 日志级别 */
    logLevel?: 'debug' | 'info' | 'warn' | 'error';
}
/**
 * 健康检查结果
 */
export interface HealthCheckResult {
    /** 服务名称 */
    serviceName: string;
    /** 是否健康 */
    healthy: boolean;
    /** 响应时间（毫秒） */
    responseTime?: number;
    /** 错误信息 */
    error?: string;
    /** 检查时间戳 */
    timestamp: number;
}
/**
 * 服务事件
 */
export interface ServiceEvent {
    type: 'started' | 'stopped' | 'error' | 'restarting' | 'healthcheck';
    serviceName: string;
    timestamp: number;
    details?: any;
}
/**
 * 指标收集
 */
export interface Metrics {
    /** 请求计数 */
    requestCount: number;
    /** 成功请求数 */
    successCount: number;
    /** 失败请求数 */
    failureCount: number;
    /** 平均响应时间（毫秒） */
    avgResponseTime: number;
    /** 最大响应时间（毫秒） */
    maxResponseTime: number;
    /** 最小响应时间（毫秒） */
    minResponseTime: number;
    /** 缓存命中率（%） */
    cacheHitRate?: number;
    /** 当前并发数 */
    currentConcurrency: number;
}
//# sourceMappingURL=types.d.ts.map