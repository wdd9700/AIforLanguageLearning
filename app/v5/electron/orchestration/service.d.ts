/**
 * Service Base Classes - 服务抽象层
 * 提供进程服务和 HTTP 服务的基类实现
 */
import { ServiceConfig, ServiceInstance, ServiceStatus, HealthCheckResult } from './types.js';
/**
 * 服务基类
 */
export declare abstract class BaseService {
    protected config: ServiceConfig;
    protected instance: ServiceInstance;
    protected healthCheckTimer?: NodeJS.Timeout;
    constructor(config: ServiceConfig);
    /**
     * 获取服务实例信息
     */
    getInstance(): ServiceInstance;
    /**
     * 获取服务名称
     */
    getName(): string;
    /**
     * 获取服务状态
     */
    getStatus(): ServiceStatus;
    /**
     * 启动服务
     */
    abstract start(): Promise<void>;
    /**
     * 停止服务
     */
    abstract stop(): Promise<void>;
    /**
     * 健康检查
     */
    abstract healthCheck(): Promise<HealthCheckResult>;
    /**
     * 调用服务（发送请求）
     */
    abstract invoke(method: string, params: any, timeout?: number): Promise<any>;
    /**
     * 预热服务
     */
    abstract warmup(): Promise<void>;
    /**
     * 更新状态
     */
    protected updateStatus(status: ServiceStatus, error?: string): void;
    /**
     * 启动健康检查
     */
    protected startHealthChecking(): void;
    /**
     * 停止健康检查
     */
    protected stopHealthChecking(): void;
    /**
     * 处理健康检查失败
     */
    protected handleHealthCheckFailure(): Promise<void>;
    /**
     * 清理资源
     */
    abstract cleanup(): Promise<void>;
}
/**
 * 进程服务（本地 CLI 工具）
 */
export declare class ProcessService extends BaseService {
    private process?;
    start(): Promise<void>;
    stop(): Promise<void>;
    healthCheck(): Promise<HealthCheckResult>;
    invoke(method: string, params: any, timeout?: number): Promise<any>;
    warmup(): Promise<void>;
    cleanup(): Promise<void>;
    /**
     * 等待服务就绪
     */
    private waitForReady;
}
/**
 * HTTP 服务（远程 API）
 */
export declare class HttpService extends BaseService {
    start(): Promise<void>;
    stop(): Promise<void>;
    healthCheck(): Promise<HealthCheckResult>;
    invoke(method: string, params: any, timeout?: number): Promise<any>;
    warmup(): Promise<void>;
    cleanup(): Promise<void>;
}
/**
 * 服务工厂
 */
export declare function createService(config: ServiceConfig): BaseService;
//# sourceMappingURL=service.d.ts.map