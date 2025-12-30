/**
 * @fileoverview 服务管理器 (Service Manager)
 * @description
 * 该文件充当后端 AI 服务的总控制器，负责统一管理 LLM, ASR, TTS, OCR 等核心服务的生命周期。
 * 
 * 主要功能：
 * 1. 统一实例化：集中创建和持有各个 Service 类的实例
 * 2. 并行初始化：启动时并行执行所有服务的 initialize 方法，提高启动速度
 * 3. 状态聚合：提供 getStatus 接口，一次性获取所有服务的当前运行状态 (ready, error, initializing 等)
 * 4. 健康检查：提供 healthCheckAll 方法，触发所有服务的自检逻辑
 * 5. 优雅关闭：在系统退出时协调所有服务的资源释放
 * 
 * 架构角色：
 * - 上层 API (Routes/Handlers) 通过 ServiceManager 访问具体的 AI 能力
 * - 屏蔽了底层服务的具体实现细节和初始化复杂性
 * 
 * 待改进项：
 * - [ ] 实现服务依赖管理 (Dependency Injection)
 * - [ ] 增加服务自动重启策略 (Crash Recovery)
 * - [ ] 支持动态加载/卸载服务插件
 * - [ ] 统一 Orchestrator 和 Managers 中的 ServiceManager 实现
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { LLMService } from '../services/llm.service';
import { ASRService } from '../services/asr.service';
import { TTSService } from '../services/tts.service';
import { OCRService } from '../services/ocr.service';
import { VoiceDialogueProcessor } from '../services/voice-dialogue-processor';
import { PromptManager } from './prompt-manager';
import { ContextManager } from './context-manager';
import { ServiceStatus } from '../services/base.service';
import { createLogger } from '../utils/logger';

const logger = createLogger('ServiceManager');

export class ServiceManager {
  public llm: LLMService;
  public asr: ASRService;
  public tts: TTSService;
  public ocr: OCRService;
  public voiceDialogue: VoiceDialogueProcessor;
  public prompt: PromptManager;
  public context: ContextManager;

  constructor() {
    // 实例化各个服务组件
    this.llm = new LLMService();
    this.asr = new ASRService();
    this.tts = new TTSService();
    this.ocr = new OCRService();
    this.prompt = new PromptManager();
    this.context = new ContextManager();
    
    // Voice Dialogue Processor (depends on this manager)
    this.voiceDialogue = new VoiceDialogueProcessor(this);
  }

  /**
   * 初始化所有服务
   * 并行启动所有服务的初始化流程，并注册状态变更监听器
   */
  async initialize(): Promise<void> {
    logger.info('Initializing Services...');
    
    // 并行初始化以加快启动速度
    await Promise.all([
      this.llm.initialize(),
      this.asr.initialize(),
      this.tts.initialize(),
      this.ocr.initialize(),
      this.voiceDialogue.start() // Start Voice Dialogue Processor
    ]);

    // 监听各个服务的状态变化事件，统一记录日志
    this.llm.on('statusChange', (s: ServiceStatus) => logger.info({ service: 'LLM', status: s }, 'Status Changed'));
    this.asr.on('statusChange', (s: ServiceStatus) => logger.info({ service: 'ASR', status: s }, 'Status Changed'));
    this.tts.on('statusChange', (s: ServiceStatus) => logger.info({ service: 'TTS', status: s }, 'Status Changed'));
    this.ocr.on('statusChange', (s: ServiceStatus) => logger.info({ service: 'OCR', status: s }, 'Status Changed'));

    logger.info('All Services Initialized');
  }

  /**
   * 执行全量健康检查
   * 触发所有服务的健康检查逻辑
   */
  async healthCheckAll(): Promise<void> {
    await Promise.all([
      this.llm.healthCheck(),
      this.asr.healthCheck(),
      this.tts.healthCheck(),
      this.ocr.healthCheck()
    ]);
  }

  /**
   * 激活并获取指定服务实例
   * 用于 Orchestrator 动态调用服务
   * 
   * @param name 服务名称 (llm, asr, tts, ocr)
   * @returns 服务实例
   */
  async activate(name: string): Promise<any> {
    switch (name) {
      case 'llm':
        return this.llm;
      case 'asr':
        return this.asr;
      case 'tts':
        return this.tts;
      case 'ocr':
        return this.ocr;
      default:
        throw new Error(`Service ${name} not found`);
    }
  }

  /**
   * 获取当前所有服务的状态快照
   * @returns 包含各服务状态的对象
   */
  getStatus(): Record<string, ServiceStatus> {
    return {
      llm: this.llm.getStatus(),
      asr: this.asr.getStatus(),
      tts: this.tts.getStatus(),
      ocr: this.ocr.getStatus()
    };
  }

  /**
   * 运行系统自检
   * 依次检查关键服务组件的健康状况，并记录警告日志
   */
  async runSelfTest(): Promise<void> {
    logger.info('Running System Self-Test...');
    
    // 1. 检查 LLM 服务 (核心对话能力)
    const llmOk = await this.llm.healthCheck();
    if (!llmOk) logger.warn('LLM Health Check Failed');

    // 2. 检查语音服务 (ASR/TTS)
    const asrOk = await this.asr.healthCheck();
    const ttsOk = await this.tts.healthCheck();
    
    if (!asrOk) logger.warn('ASR Health Check Failed');
    if (!ttsOk) logger.warn('TTS Health Check Failed');
    
    logger.info({ llmOk, asrOk, ttsOk }, 'Self-Test Completed');
  }

  /**
   * 优雅关闭所有服务
   * 释放资源，断开连接
   */
  async shutdown(): Promise<void> {
    await Promise.all([
      this.llm.shutdown(),
      this.asr.shutdown(),
      this.tts.shutdown(),
      this.ocr.shutdown(),
      this.voiceDialogue.stop()
    ]);
  }
}
