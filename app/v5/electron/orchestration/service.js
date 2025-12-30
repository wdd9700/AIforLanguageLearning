/**
 * Service Base Classes - 服务抽象层
 * 提供进程服务和 HTTP 服务的基类实现
 */
import log from 'electron-log';
import { spawn } from 'node:child_process';
import { ServiceStatus } from './types.js';
/**
 * 服务基类
 */
export class BaseService {
    config;
    instance;
    healthCheckTimer;
    constructor(config) {
        this.config = config;
        this.instance = {
            name: config.name,
            status: ServiceStatus.STOPPED,
            restartCount: 0,
        };
    }
    /**
     * 获取服务实例信息
     */
    getInstance() {
        return this.instance;
    }
    /**
     * 获取服务名称
     */
    getName() {
        return this.config.name;
    }
    /**
     * 获取服务状态
     */
    getStatus() {
        return this.instance.status;
    }
    /**
     * 更新状态
     */
    updateStatus(status, error) {
        this.instance.status = status;
        if (error) {
            this.instance.error = error;
        }
        else {
            delete this.instance.error;
        }
        if (status === ServiceStatus.RUNNING) {
            this.instance.startedAt = Date.now();
            this.instance.lastHeartbeat = Date.now();
        }
        log.info(`Service ${this.config.name} status: ${status}`, error ? `(${error})` : '');
    }
    /**
     * 启动健康检查
     */
    startHealthChecking() {
        const interval = this.config.healthCheckInterval || 30000;
        this.healthCheckTimer = setInterval(async () => {
            try {
                if (this.instance.status !== ServiceStatus.RUNNING)
                    return;
                const result = await this.healthCheck();
                if (!result.healthy) {
                    log.warn(`Health check failed for ${this.config.name}: ${result.error}`);
                    // 触发重启或错误处理
                    await this.handleHealthCheckFailure();
                }
                else {
                    this.instance.lastHeartbeat = Date.now();
                }
            }
            catch (error) {
                log.error('Health check error:', error);
            }
        }, interval);
    }
    /**
     * 停止健康检查
     */
    stopHealthChecking() {
        if (this.healthCheckTimer) {
            clearInterval(this.healthCheckTimer);
            this.healthCheckTimer = undefined;
        }
    }
    /**
     * 处理健康检查失败
     */
    async handleHealthCheckFailure() {
        if (!this.config.autoRestartCount || this.instance.restartCount < this.config.autoRestartCount) {
            log.warn(`Restarting service ${this.config.name} (attempt ${this.instance.restartCount + 1})`);
            const delay = this.config.autoRestartDelay || 1000;
            await new Promise(resolve => setTimeout(resolve, delay));
            this.instance.restartCount++;
            try {
                await this.stop();
                await this.start();
            }
            catch (error) {
                log.error('Restart failed:', error);
            }
        }
        else {
            this.updateStatus(ServiceStatus.ERROR, 'Max restart attempts exceeded');
        }
    }
}
/**
 * 进程服务（本地 CLI 工具）
 */
export class ProcessService extends BaseService {
    process;
    async start() {
        if (this.instance.status === ServiceStatus.RUNNING) {
            log.warn(`Service ${this.config.name} is already running`);
            return;
        }
        if (!this.config.command) {
            throw new Error(`No command configured for service ${this.config.name}`);
        }
        this.updateStatus(ServiceStatus.STARTING);
        try {
            const [cmd, ...args] = this.config.command.split(' ');
            this.process = spawn(cmd, args, {
                cwd: this.config.cwd || process.cwd(),
                env: { ...process.env, ...this.config.env },
                stdio: ['pipe', 'pipe', 'pipe'],
            });
            this.process.stdout?.on('data', (data) => {
                log.debug(`[${this.config.name}] stdout:`, data.toString().trim());
            });
            this.process.stderr?.on('data', (data) => {
                log.debug(`[${this.config.name}] stderr:`, data.toString().trim());
            });
            this.process.on('error', (error) => {
                log.error(`Process error for ${this.config.name}:`, error);
                this.updateStatus(ServiceStatus.ERROR, error.message);
            });
            this.process.on('close', (code) => {
                log.info(`Process ${this.config.name} closed with code ${code}`);
                this.updateStatus(ServiceStatus.STOPPED);
            });
            this.instance.pid = this.process.pid;
            // 等待服务就绪
            const timeout = this.config.startTimeout || 30000;
            await this.waitForReady(timeout);
            this.updateStatus(ServiceStatus.RUNNING);
            this.startHealthChecking();
            log.info(`Service ${this.config.name} started successfully (PID: ${this.instance.pid})`);
        }
        catch (error) {
            this.updateStatus(ServiceStatus.ERROR, error instanceof Error ? error.message : String(error));
            throw error;
        }
    }
    async stop() {
        this.stopHealthChecking();
        if (this.process) {
            return new Promise((resolve, reject) => {
                if (!this.process) {
                    resolve();
                    return;
                }
                const timeout = setTimeout(() => {
                    this.process?.kill('SIGKILL');
                    reject(new Error(`Failed to stop service ${this.config.name} gracefully`));
                }, 5000);
                this.process.once('exit', () => {
                    clearTimeout(timeout);
                    this.updateStatus(ServiceStatus.STOPPED);
                    this.process = undefined;
                    resolve();
                });
                this.process.kill('SIGTERM');
            });
        }
        this.updateStatus(ServiceStatus.STOPPED);
    }
    async healthCheck() {
        const result = {
            serviceName: this.config.name,
            healthy: this.process !== undefined && !this.process.killed,
            timestamp: Date.now(),
        };
        if (this.config.healthCheck) {
            try {
                const startTime = Date.now();
                // 可以实现具体的健康检查逻辑
                result.responseTime = Date.now() - startTime;
            }
            catch (error) {
                result.healthy = false;
                result.error = error instanceof Error ? error.message : String(error);
            }
        }
        return result;
    }
    async invoke(method, params, timeout) {
        throw new Error('ProcessService.invoke() not implemented. Use HTTP service or custom handler.');
    }
    async warmup() {
        if (this.config.warmupScript) {
            log.info(`Warming up service ${this.config.name}...`);
            // 可以执行预热脚本
            await new Promise(resolve => setTimeout(resolve, 1000));
            log.info(`Service ${this.config.name} warmed up`);
        }
    }
    async cleanup() {
        await this.stop();
    }
    /**
     * 等待服务就绪
     */
    async waitForReady(timeout) {
        const startTime = Date.now();
        while (Date.now() - startTime < timeout) {
            if (this.process?.killed || !this.process) {
                throw new Error(`Service ${this.config.name} exited unexpectedly`);
            }
            // 简单的就绪检查（可扩展为 HTTP 检查）
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        throw new Error(`Service ${this.config.name} startup timeout`);
    }
}
/**
 * HTTP 服务（远程 API）
 */
export class HttpService extends BaseService {
    async start() {
        if (!this.config.endpoint) {
            throw new Error(`No endpoint configured for service ${this.config.name}`);
        }
        this.updateStatus(ServiceStatus.STARTING);
        try {
            // 进行初始连接测试
            const result = await this.healthCheck();
            if (!result.healthy) {
                throw new Error(result.error || 'Health check failed');
            }
            this.updateStatus(ServiceStatus.RUNNING);
            this.startHealthChecking();
            log.info(`HTTP service ${this.config.name} connected to ${this.config.endpoint}`);
        }
        catch (error) {
            this.updateStatus(ServiceStatus.ERROR, error instanceof Error ? error.message : String(error));
            throw error;
        }
    }
    async stop() {
        this.stopHealthChecking();
        this.updateStatus(ServiceStatus.STOPPED);
        log.info(`Service ${this.config.name} stopped`);
    }
    async healthCheck() {
        const result = {
            serviceName: this.config.name,
            healthy: false,
            timestamp: Date.now(),
        };
        if (!this.config.endpoint || !this.config.healthCheck) {
            result.healthy = true;
            return result;
        }
        try {
            const startTime = Date.now();
            const url = `${this.config.endpoint}${this.config.healthCheck}`;
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            try {
                const response = await fetch(url, {
                    method: 'GET',
                    signal: controller.signal
                });
                clearTimeout(timeoutId);
                result.responseTime = Date.now() - startTime;
                result.healthy = response.ok;
                if (!response.ok) {
                    result.error = `HTTP ${response.status}: ${response.statusText}`;
                }
            }
            catch (error) {
                clearTimeout(timeoutId);
                throw error;
            }
        }
        catch (error) {
            result.healthy = false;
            result.error = error instanceof Error ? error.message : String(error);
        }
        return result;
    }
    async invoke(method, params, timeout) {
        if (!this.config.endpoint) {
            throw new Error(`No endpoint configured for service ${this.config.name}`);
        }
        try {
            // Handle special case for query/vocabulary which maps to LLM
            // The method passed here is the topic (e.g. 'query/vocabulary')
            // But the LLM endpoint expects /v1/chat/completions
            let url = `${this.config.endpoint}/${method}`;
            let body = params;
            // Special handling for LLM service
            if (this.config.name === 'llm') {
                // If method is a topic like 'query/vocabulary', we need to adapt it
                if (method === 'query/vocabulary') {
                    url = `${this.config.endpoint}/v1/chat/completions`;
                    // Construct LLM request from vocabulary query
                    const word = params.word;
                    const prompt = `Explain the word "${word}" for a language learner. 
              Return ONLY a JSON object with the following format:
              {
                "word": "${word}",
                "pronunciation": "/.../",
                "pos": "part of speech",
                "meaning": "definition in Chinese",
                "difficulty": "level (e.g. Beginner, Intermediate)",
                "examples": ["example sentence 1", "example sentence 2"]
              }`;
                    body = {
                        // Use configured model name or fallback
                        model: this.config.options?.modelName || "qwen3-vl-8b-instruct",
                        messages: [
                            { role: "system", content: "You are a helpful dictionary assistant. You always respond with valid JSON." },
                            { role: "user", content: prompt }
                        ],
                        stream: false,
                        response_format: { type: "json_object" } // Request JSON mode if supported
                    };
                }
                else if (method.startsWith('svc/llm')) {
                    // Direct LLM call
                    url = `${this.config.endpoint}/v1/chat/completions`;
                }
            }
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeout || 30000);
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                    signal: controller.signal,
                });
                clearTimeout(timeoutId);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                const data = await response.json();
                // Adapt response for vocabulary query
                if (this.config.name === 'llm' && method === 'query/vocabulary') {
                    const content = data.choices?.[0]?.message?.content || "";
                    let parsedData;
                    try {
                        // Try to find JSON block if mixed with text
                        const jsonMatch = content.match(/\{[\s\S]*\}/);
                        if (jsonMatch) {
                            parsedData = JSON.parse(jsonMatch[0]);
                        }
                        else {
                            parsedData = JSON.parse(content);
                        }
                    }
                    catch (e) {
                        // Fallback if not JSON
                        parsedData = {
                            word: params.word,
                            difficulty: "General",
                            pronunciation: "",
                            pos: "",
                            meaning: content,
                            examples: []
                        };
                    }
                    return {
                        success: true,
                        data: {
                            word: parsedData.word || params.word,
                            difficulty: parsedData.difficulty || "General",
                            pronunciation: parsedData.pronunciation || "",
                            pos: parsedData.pos || "",
                            meaning: parsedData.meaning || content,
                            examples: parsedData.examples || []
                        }
                    };
                }
                return data;
            }
            catch (error) {
                clearTimeout(timeoutId);
                throw error;
            }
        }
        catch (error) {
            log.error(`Invoke failed for ${this.config.name}.${method}:`, error);
            throw error;
        }
    }
    async warmup() {
        if (this.config.warmupScript) {
            log.info(`Warming up HTTP service ${this.config.name}...`);
            try {
                await this.invoke('warmup', {});
            }
            catch (error) {
                log.warn(`Warmup failed for ${this.config.name}:`, error);
            }
        }
    }
    async cleanup() {
        await this.stop();
    }
}
/**
 * 服务工厂
 */
export function createService(config) {
    switch (config.type) {
        case 'process':
            return new ProcessService(config);
        case 'http':
            return new HttpService(config);
        default:
            throw new Error(`Unknown service type: ${config.type}`);
    }
}
//# sourceMappingURL=service.js.map