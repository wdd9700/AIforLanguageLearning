import { Request, Response } from 'express';
import { ServiceManager } from '../managers/service-manager';
import { SessionManager } from '../managers/session-manager';
import { ConfigManager } from '../managers/config-manager';
import { config } from '../config/env';
import { updateEnvFile } from '../utils/env-writer';

export class SystemController {
  private serviceManager: ServiceManager;
  private sessionManager: SessionManager;

  constructor(serviceManager: ServiceManager, sessionManager: SessionManager) {
    this.serviceManager = serviceManager;
    this.sessionManager = sessionManager;
  }

  /**
   * 获取系统健康状态
   * 
   * 检查并返回系统的健康状况，包括各个服务（LLM, ASR, TTS, OCR）的运行状态和会话统计信息。
   * 支持通过查询参数 `refresh=true` 强制刷新服务状态检查。
   * 
   * @param req Express 请求对象，包含查询参数 refresh (可选)
   * @param res Express 响应对象
   */
  public getHealth = async (req: Request, res: Response) => {
    const shouldRefresh = req.query.refresh === 'true' || req.query.refresh === '1';
    
    if (shouldRefresh) {
      await this.serviceManager.healthCheckAll();
    }
    
    const serviceStatus = this.serviceManager.getStatus();
    const sessionStats = this.sessionManager.getStats();

    res.json({
      success: true,
      data: {
        status: 'ok',
        timestamp: Date.now(),
        services: serviceStatus,
        sessions: sessionStats,
      },
    });
  };

  /**
   * 获取当前系统配置
   * 
   * 返回系统当前的配置信息，包括端口、LLM 端点、模型配置、提示词模板以及 OCR、TTS、ASR 服务的配置。
   * 
   * @param req Express 请求对象
   * @param res Express 响应对象
   */
  public getConfig = (req: Request, res: Response) => {
    const appConfig = ConfigManager.getInstance().getConfig();
    res.json({
      success: true,
      data: {
        port: config.port,
        llmEndpoint: appConfig.services.llm.endpoints.chat,
        models: appConfig.services.llm.models,
        prompts: appConfig.prompts,
        ocr: config.services.ocr,
        tts: config.services.tts,
        asr: config.services.asr
      }
    });
  };

  /**
   * 更新系统配置
   * 
   * 更新系统的配置信息，包括模型选择、提示词模板以及各服务的参数。
   * 更新后的配置会应用到内存中，并持久化保存到 .env 文件中，以便重启后生效。
   * 支持部分更新。
   * 
   * @param req Express 请求对象，包含新的配置对象 (req.body)
   * @param res Express 响应对象
   */
  public updateConfig = (req: Request, res: Response) => {
    const newConfig = req.body;
    
    if (!newConfig || typeof newConfig !== 'object') {
        res.status(400).json({ success: false, error: 'Invalid configuration data provided.' });
        return;
    }

    // Update memory config
    if (newConfig.models && typeof newConfig.models === 'object') {
        const currentModels = config.services.llm.models as any;
        Object.assign(currentModels, newConfig.models);
    }
    
    if (newConfig.prompts && typeof newConfig.prompts === 'object') {
        const currentPrompts = (config.services.llm as any).prompts;
        if (currentPrompts) {
             Object.assign(currentPrompts, newConfig.prompts);
        }
    }

    if (newConfig.ocr && typeof newConfig.ocr === 'object') {
        Object.assign(config.services.ocr, newConfig.ocr);
    }

    if (newConfig.tts && typeof newConfig.tts === 'object') {
        Object.assign(config.services.tts, newConfig.tts);
    }

    if (newConfig.asr && typeof newConfig.asr === 'object') {
        Object.assign(config.services.asr, newConfig.asr);
    }
    
    // Persist to .env
    try {
        const updates: Record<string, string> = {};

        // Update LLM Models
        if (newConfig.models) {
            if (typeof newConfig.models.conversation === 'string') updates['LLM_MODEL_CONVERSATION'] = newConfig.models.conversation;
            if (typeof newConfig.models.vocabulary === 'string') updates['LLM_MODEL_VOCABULARY'] = newConfig.models.vocabulary;
            if (typeof newConfig.models.ocr === 'string') updates['LLM_MODEL_OCR'] = newConfig.models.ocr;
            if (typeof newConfig.models.analysis === 'string') updates['LLM_MODEL_ANALYSIS'] = newConfig.models.analysis;
            if (typeof newConfig.models.essay_correction === 'string') updates['LLM_MODEL_ESSAY'] = newConfig.models.essay_correction;
        }

        // Update Prompts
        if (newConfig.prompts) {
            const escape = (str: string) => str.replace(/"/g, '\\"');
            
            if (typeof newConfig.prompts.vocabulary === 'string') updates['PROMPT_VOCABULARY'] = `"${escape(newConfig.prompts.vocabulary)}"`;
            if (typeof newConfig.prompts.essay === 'string') updates['PROMPT_ESSAY'] = `"${escape(newConfig.prompts.essay)}"`;
            if (typeof newConfig.prompts.dialogue === 'string') updates['PROMPT_DIALOGUE'] = `"${escape(newConfig.prompts.dialogue)}"`;
            if (typeof newConfig.prompts.analysis === 'string') updates['PROMPT_ANALYSIS'] = `"${escape(newConfig.prompts.analysis)}"`;
        }

        updateEnvFile(updates);
        ConfigManager.getInstance().reload();
        res.json({ success: true, message: 'Configuration updated and saved.' });
    } catch (error: any) {
        res.status(500).json({ success: false, error: 'Failed to save config: ' + error.message });
    }
  };

  /**
   * 重启指定服务
   * 
   * 根据服务名称重启相应的后台服务（如 ASR 或 TTS）。
   * 这通常用于在服务出现故障或配置更改后重新初始化服务进程。
   * 
   * @param req Express 请求对象，包含服务名称 (req.params.service)
   * @param res Express 响应对象
   */
  public restartService = async (req: Request, res: Response) => {
      const service = req.params.service;
      
      try {
        if (service === 'asr') {
          this.serviceManager.asr.start();
          res.json({ success: true, message: 'ASR Service restarted' });
        } else if (service === 'tts') {
          this.serviceManager.tts.start();
          res.json({ success: true, message: 'TTS Service restarted' });
        } else {
          res.json({ success: true, message: `Restart signal sent: ${service}` });
        }
      } catch (error: any) {
        res.status(500).json({ success: false, error: error.message });
      }
  };

  /**
   * 列出 LLM 模型
   * 
   * 获取当前 LLM 服务中所有可用和已加载的模型列表。
   * 返回数据区分已加载 (loaded) 和可用但未加载 (available) 的模型。
   * 
   * @param req Express 请求对象
   * @param res Express 响应对象
   */
  public listModels = async (req: Request, res: Response) => {
    try {
      const result = await this.serviceManager.llm.listModels();
      
      if (result.ok) {
        res.json({ 
          success: true, 
          data: {
            models: result.models || [],
            loaded: (result.models || []).filter((m: any) => m.loaded),
            available: (result.models || []).filter((m: any) => !m.loaded)
          }
        });
      } else {
        res.status(500).json({ success: false, error: result.error });
      }
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 加载 LLM 模型
   * 
   * 请求 LLM 服务加载指定的模型文件。
   * 
   * @param req Express 请求对象，包含模型路径 (req.body.modelPath) 和额外参数 (req.body.extraArgs)
   * @param res Express 响应对象
   */
  public loadModel = async (req: Request, res: Response) => {
    try {
      const { modelPath, extraArgs } = req.body;
      
      if (!modelPath) {
        res.status(400).json({ success: false, error: 'Missing modelPath parameter' });
        return;
      }
      
      const result = await this.serviceManager.llm.loadModel(modelPath, extraArgs);
      
      if (result.ok) {
        res.json({ 
          success: true, 
          message: `Model ${modelPath} loaded successfully`,
          output: result.stdout
        });
      } else {
        res.status(500).json({ 
          success: false, 
          error: result.error,
          stderr: result.stderr
        });
      }
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 卸载 LLM 模型
   * 
   * 请求 LLM 服务卸载指定的模型实例，释放资源。
   * 
   * @param req Express 请求对象，包含模型标识符 (req.body.identifier)
   * @param res Express 响应对象
   */
  public unloadModel = async (req: Request, res: Response) => {
    try {
      const { identifier } = req.body;
      
      if (!identifier) {
        res.status(400).json({ success: false, error: 'Missing identifier parameter' });
        return;
      }
      
      const result = await this.serviceManager.llm.unloadModel(identifier);
      
      if (result.ok) {
        res.json({ 
          success: true, 
          message: `Model ${identifier} unloaded successfully`,
          output: result.stdout
        });
      } else {
        res.status(500).json({ 
          success: false, 
          error: result.error,
          stderr: result.stderr
        });
      }
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 扩展场景描述
   * 
   * 使用 LLM 将简短的场景描述扩展为详细的角色扮演系统提示词 (System Prompt)。
   * 这用于帮助用户快速创建丰富的对话场景。
   * 
   * @param req Express 请求对象，包含场景描述 (req.body.scenario)
   * @param res Express 响应对象
   */
  public expandScenario = async (req: Request, res: Response) => {
    try {
      const { scenario } = req.body;
      if (!scenario) {
        res.status(400).json({ success: false, error: 'Scenario description is required' });
        return;
      }
      
      const prompt = `Please expand the following scenario description into a detailed system prompt for a language learning role-play: "${scenario}"`;
      const result = await this.serviceManager.llm.invoke({
        prompt,
        task: 'analysis',
        maxTokens: 500,
        temperature: 0.7
      });
      const expandedPrompt = result.response;
      res.json({ success: true, data: { prompt: expandedPrompt } });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 高级模型加载
   * 
   * 提供更细粒度的参数控制来加载 LLM 模型，支持 GPU 层数、上下文长度、TTL 等高级配置。
   * 
   * @param req Express 请求对象，包含模型路径及各种高级参数 (gpu, contextLength, ttl, identifier, etc.)
   * @param res Express 响应对象
   */
  public loadModelAdvanced = async (req: Request, res: Response) => {
    try {
      const { modelPath, gpu, contextLength, ttl, identifier, exact, yes, estimateOnly } = req.body;
      
      if (!modelPath) {
        res.status(400).json({ success: false, error: 'Missing modelPath parameter' });
        return;
      }
      
      const args: string[] = [];
      if (gpu !== undefined && gpu !== null) args.push(`--gpu ${gpu}`);
      if (contextLength !== undefined && contextLength !== null) args.push(`--context-length ${contextLength}`);
      if (ttl !== undefined && ttl !== null && ttl > 0) args.push(`--ttl ${ttl}`);
      if (identifier !== undefined && identifier !== null && identifier !== '') args.push(`--identifier ${identifier}`);
      if (exact === true) args.push('--exact');
      if (yes === true) args.push('-y');
      if (estimateOnly === true) args.push('--estimate-only');
      
      const extraArgs = args.length > 0 ? args.join(' ') : undefined;
      const result = await this.serviceManager.llm.loadModel(modelPath, extraArgs);
      
      if (result.ok) {
        res.json({ 
          success: true, 
          message: `Model ${modelPath} loaded successfully`,
          output: result.stdout,
          params: { modelPath, gpu, contextLength, ttl, identifier, exact, yes, estimateOnly }
        });
      } else {
        res.status(500).json({ 
          success: false, 
          error: result.error,
          stderr: result.stderr
        });
      }
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 获取服务参数详情
   * 
   * 返回各个后端服务（LLM, ASR, TTS, OCR）的详细配置参数，如脚本路径、超时设置、启用状态等。
   * 
   * @param req Express 请求对象
   * @param res Express 响应对象
   */
  public getServiceParams = (req: Request, res: Response) => {
    res.json({
      success: true,
      data: {
        llm: {
          endpoint: config.services.llm.endpoint,
          timeout: config.services.llm.timeout,
          models: config.services.llm.models
        },
        asr: {
          scriptPath: config.services.asr.scriptPath,
          pythonPath: config.services.asr.pythonPath,
          timeout: config.services.asr.timeout
        },
        tts: {
          scriptPath: config.services.tts.scriptPath,
          timeout: config.services.tts.timeout
        },
        ocr: {
          enabled: config.services.ocr.enabled
        }
      }
    });
  };
}
