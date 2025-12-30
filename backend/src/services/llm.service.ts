/**
 * @fileoverview LLM 服务 (Large Language Model Service)
 * 
 * 负责与后端 LLM 推理引擎 (如 LM Studio, Ollama, LocalAI) 进行交互。
 * 提供了模型管理、健康探测、任务路由和对话生成等核心功能。
 * 
 * 主要功能：
 * 1. 模型管理 (LMS CLI)：通过命令行工具管理本地模型的加载、卸载和列表查询
 * 2. 健康探测 (Probe)：定期检查 LLM API 可达性和当前加载的模型
 * 3. 任务路由 (Match)：根据任务类型 (conversation, vocabulary, etc.) 自动匹配最佳模型
 * 4. 对话生成 (Invoke)：封装 OpenAI 兼容的 Chat Completion API，支持 JSON 模式和系统提示词注入
 * 
 * 待改进项：
 * - [ ] 支持流式响应 (Streaming Response) 以降低首字延迟
 * - [ ] 增加 Token 计费和限流功能
 * - [ ] 优化模型加载策略，支持按需自动加载
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { BaseService } from './base.service';
import { config } from '../config/env';
import { ConfigManager } from '../managers/config-manager';
import axios, { AxiosInstance } from 'axios';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export interface LLMRequest {
  prompt: string;
  history?: any[];
  task?: 'conversation' | 'vocabulary' | 'ocr' | 'analysis' | 'essay_correction' | 'learning_analysis' | 'prompt_expansion' | 'default' | string;
  systemPrompt?: string; // Allow overriding system prompt per request
  maxTokens?: number;
  temperature?: number;
  jsonMode?: boolean; // 是否强制 JSON 输出
  stream?: boolean; // 是否启用流式输出
  onToken?: (token: string) => void; // 流式输出回调
}

export interface LLMResponse {
  response: string;
  tokenUsage?: any;
  parsedJson?: any; // 如果 jsonMode 为 true，尝试解析的结果
}

export class LLMService extends BaseService {
  private client: AxiosInstance | null = null;
  private effectiveModels: Map<string, string> = new Map();
  private apiReachable: boolean = false;
  private modelAvailable: boolean = false;

  constructor() {
    super('llm');
  }

  /**
   * 执行 LMS 命令行工具
   * 用于管理本地模型 (加载/卸载/列表)
   */
  protected async runLMSCommand(command: string): Promise<{ ok: boolean; stdout?: string; stderr?: string; error?: string }> {
    try {
      const { stdout, stderr } = await execAsync(command);
      return { ok: true, stdout: stdout.trim(), stderr: stderr.trim() };
    } catch (error: any) {
      return { ok: false, error: error.message, stderr: error.stderr?.trim() };
    }
  }

  /**
   * Helper to safely extract JSON array from a string that might contain other text
   */
  private extractJsonArray(str: string): any[] {
    try {
        const start = str.indexOf('[');
        const end = str.lastIndexOf(']');
        if (start !== -1 && end !== -1 && end > start) {
            const jsonStr = str.substring(start, end + 1);
            const result = JSON.parse(jsonStr);
            return Array.isArray(result) ? result : [];
        }
        const result = JSON.parse(str);
        return Array.isArray(result) ? result : [];
    } catch (e) {
        return [];
    }
  }

  /**
   * 列出可用模型
   * 优先尝试 LMS CLI，失败则回退到 API
   */
  async listModels(options?: { host?: string; port?: number; only?: 'llm' | 'embedding' }): Promise<{ ok: boolean, models: any[], error?: string }> {
    // 1. Try CLI first
    try {
        const filters = options?.only === 'llm' 
        ? ' --llm' 
        : (options?.only === 'embedding' ? ' --embedding' : '');
        
        const inst: string[] = [];
        if (options?.host) inst.push(`--host ${options.host}`);
        if (options?.port) inst.push(`--port ${options.port}`);
        
        const cmd = `${config.services.llm.lmsCommand} ls --json${filters}${inst.length ? ' ' + inst.join(' ') : ''}`;
        const result = await this.runLMSCommand(cmd);
        
        if (result.ok) {
            const raw = result.stdout || '[]';
            const models = this.extractJsonArray(raw);
            
            if (models.length > 0) {
                return { ok: true, models };
            }
        }
    } catch (e) {
        this.logger.warn({ err: e }, 'LMS CLI list failed, falling back to API');
    }

    // 2. Fallback to API
    if (this.client) {
        try {
            const response = await this.client.get('/v1/models');
            // Handle various API response formats
            let models = [];
            if (Array.isArray(response.data)) {
                models = response.data;
            } else if (response.data && Array.isArray(response.data.data)) {
                models = response.data.data;
            }
            return { ok: true, models };
        } catch (e: any) {
            this.logger.error({ err: e }, 'Failed to list models via API');
            return { ok: false, models: [], error: e.message };
        }
    }

    return { ok: false, models: [], error: 'No client available' };
  }

  /**
   * 获取已加载的模型列表
   * 优先尝试 LMS CLI ps 命令，失败则回退到 API 查询
   */
  async getLoadedModels(): Promise<any[]> {
    // 1. Try CLI first
    const cmd = `${config.services.llm.lmsCommand} ps --json`;
    const result = await this.runLMSCommand(cmd);
    
    if (result.ok) {
      return this.extractJsonArray(result.stdout || '[]');
    }
    
    // 2. Fallback to API
    if (this.client) {
        try {
            const response = await this.client.get('/v1/models');
            let models = [];
            if (Array.isArray(response.data)) {
                models = response.data;
            } else if (response.data && Array.isArray(response.data.data)) {
                models = response.data.data;
            }
            // Map API response to expected format
            // API usually returns { id: "model-id", ... }
            // CLI returns { identifier: "model-id", ... }
            return models.map((m: any) => ({
                identifier: m.id,
                modelKey: m.id,
                ...m
            }));
        } catch (e) {
            this.logger.warn({ err: e }, 'Failed to list loaded models via API');
        }
    }

    return [];
  }

  /**
   * 加载模型
   */
  async loadModel(modelPath: string, extraArgs?: string): Promise<{ ok: boolean; stdout?: string; stderr?: string; error?: string }> {
      const cmd = `${config.services.llm.lmsCommand} load ${modelPath} ${extraArgs || ''}`;
      return this.runLMSCommand(cmd);
  }

  /**
   * 卸载模型
   */
  async unloadModel(identifier: string): Promise<{ ok: boolean; stdout?: string; stderr?: string; error?: string }> {
      const cmd = `${config.services.llm.lmsCommand} unload ${identifier}`;
      return this.runLMSCommand(cmd);
  }

  /**
   * 初始化 LLM 服务
   * 配置 Axios 客户端并启动健康探测
   */
  async initialize(): Promise<void> {
    const llmBaseUrl = config.services.llm.endpoint
      .replace(/\/v1\/.*$/, '')
      .replace(/\/$/, '');

    this.client = axios.create({
      baseURL: llmBaseUrl,
      timeout: config.services.llm.timeout,
      headers: { 'Content-Type': 'application/json' },
    });

    this.logger.info({ llmBaseUrl }, 'LLM Service initialized');
    
    // 初始探测
    await this.probe();
    
    // 定期探测 (每10秒)
    setInterval(() => this.probe(), 10000);
  }

  async shutdown(): Promise<void> {
    this.client = null;
    this.updateStatus('stopped');
  }

  async healthCheck(): Promise<boolean> {
    await this.probe();
    return this.apiReachable && this.modelAvailable;
  }

  /**
   * 探测 LLM API 和可用模型
   */
  private async probe(): Promise<void> {
    if (!this.client) return;

    try {
      // 1. Check API Reachability
      await this.client.get('/v1/models', { timeout: 5000 });
      this.apiReachable = true;

      // 2. Get Loaded Models
      let loadedModels = await this.getLoadedModels();
      
      this.modelAvailable = true; // Service is available if API is reachable (we can load models)
      
      this.updateStatus('running', 'LLM Service Ready', {
          loaded: loadedModels.map((m: any) => m.identifier || m.modelKey)
      });

    } catch (error: any) {
      this.apiReachable = false;
      this.modelAvailable = false;
      this.updateStatus('error', `LLM API Unreachable: ${error.message}`);
    }
  }

  /**
   * 确保指定任务所需的模型已加载
   * 如果未加载，则自动卸载其他模型并加载所需模型
   */
  private async ensureModelForTask(task: string): Promise<string> {
    const configuredModelId = (config.services.llm.models as any)[task];
    if (!configuredModelId) {
      // 如果没有为任务配置特定模型，使用 default 或 conversation 作为回退
      const fallback = (config.services.llm.models as any)['conversation'];
      this.logger.warn({ task, fallback }, 'No specific model configured for task, using fallback');
      return this.ensureModelLoaded(fallback);
    }
    return this.ensureModelLoaded(configuredModelId);
  }

  /**
   * 确保特定模型已加载
   */
  private async ensureModelLoaded(modelId: string): Promise<string> {
    // 1. Check if already loaded
    const loadedModels = await this.getLoadedModels();
    const isLoaded = loadedModels.some((m: any) => m.identifier === modelId || m.modelKey === modelId);
    
    if (isLoaded) {
      return modelId;
    }

    this.logger.info({ modelId }, 'Model not loaded, starting active loading process...');

    // 2. Unload ALL other models to free VRAM (Safe Strategy)
    // We assume single-GPU setup where running multiple LLMs is risky
    if (loadedModels.length > 0) {
        this.logger.info('Unloading existing models to free resources...');
        for (const m of loadedModels) {
            await this.unloadModel(m.identifier);
        }
    }

    // 3. Load the target model
    const loadConfig = (config.services.llm as any).loadConfig?.[modelId] || {};
    const args = this.buildLoadArgs(loadConfig);
    
    this.logger.info({ modelId, args }, 'Loading model...');
    const loadResult = await this.loadModel(modelId, args);
    
    if (!loadResult.ok) {
        this.logger.error({ modelId, error: loadResult.error, stderr: loadResult.stderr }, 'Failed to load model');
        throw new Error(`Failed to load model ${modelId}: ${loadResult.error}`);
    }

    // 4. Verify loading
    // Wait a moment for the server to register it
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const verifyLoaded = await this.getLoadedModels();
    const verified = verifyLoaded.some((m: any) => m.identifier === modelId || m.modelKey === modelId);
    
    if (!verified) {
        throw new Error(`Model ${modelId} reported success but not found in loaded list`);
    }

    this.logger.info({ modelId }, 'Model successfully loaded and ready');
    return modelId;
  }

  private buildLoadArgs(config: Record<string, any>): string {
      const args: string[] = [];
      for (const [key, value] of Object.entries(config)) {
          // Convert camelCase/snake_case to kebab-case flags
          // e.g. gpuOffloadRatio -> --gpu-offload-ratio
          const flag = key.replace(/[A-Z]/g, m => `-${m.toLowerCase()}`).replace(/_/g, '-');
          args.push(`--${flag} ${value}`);
      }
      return args.join(' ');
  }

  /**
   * 调用 LLM 生成回复
   * @param payload 请求参数 (prompt, history, task, etc.)
   */
  async invoke(payload: LLMRequest): Promise<LLMResponse> {
    if (!this.client) {
      throw new Error('LLM Service not initialized');
    }

    const task = payload.task || 'default';
    
    // Active Model Management: Ensure the right model is loaded
    let modelId: string;
    try {
        modelId = await this.ensureModelForTask(task);
    } catch (e: any) {
        this.logger.error({ task, error: e.message }, 'Failed to ensure model for task');
        throw e;
    }

    // 1. Determine System Prompt
    // Priority: Payload Override > ConfigManager > Config Fallback > Default
    let systemPrompt = payload.systemPrompt;

    if (!systemPrompt) {
        const appConfig = ConfigManager.getInstance().getConfig();
        // Check PROMPTS in ConfigManager
        if (task in appConfig.prompts) {
            const promptConfig = (appConfig.prompts as any)[task];
            if (promptConfig && promptConfig.system) {
                systemPrompt = promptConfig.system;
            }
        } else {
            // Fallback to config.services.llm.prompts
            systemPrompt = (config.services.llm as any).prompts?.[task];
        }
    }
    
    // Default if still null
    if (!systemPrompt) {
        systemPrompt = "You are a helpful assistant.";
    }
    
    // 如果需要 JSON 模式，注入系统提示
    let finalSystemPrompt = systemPrompt;
    if (payload.jsonMode) {
      finalSystemPrompt += "\nIMPORTANT: You must output valid JSON only. No markdown code blocks, no explanations.";
    }

    const messages = [
      { role: 'system', content: finalSystemPrompt },
      ...(payload.history || []),
      { role: 'user', content: payload.prompt }
    ];

    try {
      const response = await this.client.post('/v1/chat/completions', {
        model: modelId,
        messages,
        max_tokens: payload.maxTokens || 1000,
        temperature: payload.temperature || 0.7,
        stream: payload.stream || false
      }, {
        responseType: payload.stream ? 'stream' : 'json'
      });

      if (payload.stream) {
        return new Promise((resolve, reject) => {
          let fullContent = '';
          const stream = response.data;

          stream.on('data', (chunk: Buffer) => {
            const lines = chunk.toString().split('\n');
            for (const line of lines) {
              if (line.trim() === '') continue;
              if (line.trim() === 'data: [DONE]') continue;
              if (line.startsWith('data: ')) {
                try {
                  const json = JSON.parse(line.substring(6));
                  const content = json.choices[0]?.delta?.content || "";
                  if (content) {
                    fullContent += content;
                    if (payload.onToken) {
                      payload.onToken(content);
                    }
                  }
                } catch (e) {
                  // ignore parse error
                }
              }
            }
          });

          stream.on('end', () => {
            resolve({
              response: fullContent,
              tokenUsage: { total_tokens: 0 } // Stream usually doesn't return usage in standard SSE
            });
          });

          stream.on('error', (err: any) => {
            reject(err);
          });
        });
      }

      // Check if choices exist
      if (!response.data.choices || response.data.choices.length === 0) {
          this.logger.error({ response: response.data }, 'LLM returned no choices');
          throw new Error('LLM returned no choices');
      }

      const content = response.data.choices[0]?.message?.content || '';
      
      // Validate content
      if (!content || content.trim().length === 0) {
          this.logger.error({ response: response.data }, 'LLM returned empty content');
          throw new Error('LLM returned empty content');
      }

      // Log raw content for manual inspection as requested
      this.logger.info({ contentPreview: content.substring(0, 200) + '...' }, 'LLM Response Received');

      let parsedJson = null;

      if (payload.jsonMode) {
        try {
          // 尝试清理 markdown 代码块标记
          // Robust extraction of JSON from Markdown code blocks
          const jsonMatch = content.match(/```json\s*([\s\S]*?)\s*```/) || content.match(/```\s*([\s\S]*?)\s*```/);
          const cleanContent = jsonMatch ? jsonMatch[1].trim() : content.trim();
          parsedJson = JSON.parse(cleanContent);
        } catch (e) {
          this.logger.warn({ content }, 'Failed to parse JSON from LLM response');
        }
      }

      return {
        response: content,
        tokenUsage: response.data.usage,
        parsedJson
      };

    } catch (error: any) {
      this.logger.error({ error: error.message, task }, 'LLM invocation failed');
      throw error;
    }
  }
}
