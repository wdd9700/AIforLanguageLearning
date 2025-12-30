/**
 * @fileoverview 语音对话处理器 (Voice Dialogue Processor)
 * 
 * 基于软总线 (Softbus) 的语音对话服务，负责协调 ASR、LLM 和 TTS 服务，
 * 实现端到端的语音交互流程。
 * 
 * 主要功能：
 * 1. 音频流监听：订阅客户端发布的音频数据流 (audio.pcm.*)
 * 2. 会话管理：管理对话会话的生命周期 (Start/Stop/Cleanup)
 * 3. 服务编排：按顺序调用 ASR (转写) -> LLM (生成) -> TTS (合成)
 * 4. 结果发布：将各阶段的处理结果发布回软总线，供客户端消费
 * 5. 实时流式处理：支持流式 ASR 和部分结果的实时反馈 (可选)
 * 
 * 待改进项：
 * - [ ] 移除 Mock 服务，接入真实的 ASR/LLM/TTS 服务实例
 * - [ ] 实现流式 ASR (streamASR) 逻辑
 * - [ ] 完善错误处理和重试机制
 * - [ ] 将软总线配置 (Endpoint, PSK) 移至环境变量或配置文件
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { SoftbusClient, derivePsk } from '../softbus';
import { ServiceManager } from '../managers/service-manager';
import { createLogger } from '../utils/logger';

const logger = createLogger('VoiceDialogueProcessor');

/**
 * 会话管理器
 */
class SessionManager {
  private sessions: Map<string, Session> = new Map();

  createSession(sessionId: string, language: string): Session {
    const session = new Session(sessionId, language);
    this.sessions.set(sessionId, session);
    return session;
  }

  getSession(sessionId: string): Session | undefined {
    return this.sessions.get(sessionId);
  }

  removeSession(sessionId: string): void {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.cleanup();
      this.sessions.delete(sessionId);
    }
  }
}

/**
 * 单个会话状态
 */
class Session {
  public audioChunks: Uint8Array[] = [];
  public isRecording = false;
  public transcription = '';
  public llmResponse = '';
  public createdAt = Date.now();

  constructor(
    public sessionId: string,
    public language: string
  ) {}

  cleanup(): void {
    this.audioChunks = [];
    this.isRecording = false;
  }
}

/**
 * 语音对话处理器
 */
export class VoiceDialogueProcessor {
  private softbusClient: SoftbusClient | null = null;
  private sessionManager = new SessionManager();
  private serviceManager: ServiceManager;
  private isRunning = false;

  constructor(serviceManager: ServiceManager) {
    this.serviceManager = serviceManager;
  }

  async start(): Promise<void> {
    try {
      logger.info('Starting Voice Dialogue Processor...');

      // 初始化软总线
      const psk = derivePsk('language-learning-app-2024');
      this.softbusClient = new SoftbusClient({
        endpoint: 'tcp://0.0.0.0:5555',  // 监听所有接口
        psk,
      });

      await this.softbusClient.connect();
      logger.info('Softbus connected');

      // 订阅音频流主题（所有会话）
      this.subscribeAudioStream();

      // 订阅控制信号主题
      this.subscribeControlSignals();

      // 启动心跳（可选）
      this.startHeartbeat();

      this.isRunning = true;
      logger.info('Voice Dialogue Processor started');
    } catch (error) {
      logger.error({ error }, 'Failed to start Voice Dialogue Processor');
      throw error;
    }
  }

  async stop(): Promise<void> {
    this.isRunning = false;

    if (this.softbusClient) {
      await this.softbusClient.disconnect();
      this.softbusClient = null;
    }

    console.log('[VoiceDialogue] 语音对话处理器已停止');
  }

  /**
   * 订阅音频流主题
   */
  private subscribeAudioStream(): void {
    if (!this.softbusClient) return;

    // 方案 A：订阅通配符主题（如果软总线支持）
    // this.softbusClient.subscribe({ topic: 'audio.pcm.*', ... });

    // 方案 B：动态订阅具体会话（需要先收到控制信号）
    // 这里演示方案 B

    // 临时：订阅所有已知会话格式
    // 实际应用中，客户端应该先发送 'session.start' 控制信号
    this.softbusClient.on((event) => {
      if (event.type === 'connected') {
        console.log('[VoiceDialogue] 准备接收音频流');
      }
    });
  }

  /**
   * 订阅控制信号主题
   */
  private subscribeControlSignals(): void {
    if (!this.softbusClient) return;

    // 订阅会话启动信号
    this.softbusClient.subscribe({
      topic: 'control.session.start',
      onMessage: async (msg) => {
        try {
          const control = JSON.parse(new TextDecoder().decode(msg.payload));
          console.log('[VoiceDialogue] 新会话启动:', control.sessionId);

          // 创建会话
          const session = this.sessionManager.createSession(
            control.sessionId,
            control.language || 'zh-CN'
          );
          session.isRecording = true;

          // 动态订阅该会话的音频流
          this.subscribeSessionAudio(control.sessionId);
        } catch (error) {
          console.error('[VoiceDialogue] 解析启动信号失败:', error);
        }
      },
    });

    // 订阅会话停止信号
    this.softbusClient.subscribe({
      topic: 'control.session.stop',
      onMessage: async (msg) => {
        try {
          const control = JSON.parse(new TextDecoder().decode(msg.payload));
          console.log('[VoiceDialogue] 会话停止:', control.sessionId);

          const session = this.sessionManager.getSession(control.sessionId);
          if (session) {
            session.isRecording = false;
            // 处理完整音频
            await this.processSession(control.sessionId);
          }
        } catch (error) {
          console.error('[VoiceDialogue] 解析停止信号失败:', error);
        }
      },
    });

    // 兼容旧格式：订阅通用控制主题
    // 客户端发送到 `control.<sessionId>`
    // TODO: 需要实现主题通配符匹配
  }

  /**
   * 订阅特定会话的音频流
   */
  private subscribeSessionAudio(sessionId: string): void {
    if (!this.softbusClient) return;

    const topic = `audio.pcm.${sessionId}`;
    console.log('[VoiceDialogue] 订阅音频流:', topic);

    this.softbusClient.subscribe({
      topic,
      onMessage: async (msg) => {
        const session = this.sessionManager.getSession(sessionId);
        if (!session || !session.isRecording) return;

        // 累积音频块
        session.audioChunks.push(new Uint8Array(msg.payload));
        console.log(
          `[VoiceDialogue] 收到音频块 [${sessionId}]:`,
          msg.payload.byteLength,
          'bytes, 总块数:',
          session.audioChunks.length
        );

        // 可选：实时流式 ASR
        // await this.streamASR(sessionId, msg.payload);
      },
      onError: (error) => {
        console.error(`[VoiceDialogue] 订阅音频流失败 [${sessionId}]:`, error);
      },
    });
  }

  /**
   * 处理完整会话（ASR → LLM → TTS）
   */
  private async processSession(sessionId: string): Promise<void> {
    const session = this.sessionManager.getSession(sessionId);
    if (!session || session.audioChunks.length === 0) {
      console.warn('[VoiceDialogue] 会话无音频数据:', sessionId);
      return;
    }

    try {
      console.log(`[VoiceDialogue] 开始处理会话 [${sessionId}], 音频块数: ${session.audioChunks.length}`);

      // 合并所有音频块
      const totalLength = session.audioChunks.reduce((acc, chunk) => acc + chunk.length, 0);
      const audioBuffer = new Uint8Array(totalLength);
      let offset = 0;
      for (const chunk of session.audioChunks) {
        audioBuffer.set(chunk, offset);
        offset += chunk.length;
      }

      console.log(`[VoiceDialogue] 合并音频完成: ${audioBuffer.length} bytes`);

      // Step 1: ASR 转写
      logger.info('Calling ASR service...');
      // Publish state: processing_asr
      await this.publish(`state.${sessionId}`, 'processing_asr', 'text/plain');
      
      // Use invoke for single-shot ASR
      const asrResponse = await this.serviceManager.asr.invoke(Buffer.from(audioBuffer), { 
          language: session.language 
      });
      const transcription = asrResponse.text;
      session.transcription = transcription;

      logger.info({ transcription }, 'ASR transcription completed');

      // 发布转写结果
      await this.publish(`text.${sessionId}`, transcription, 'text/plain');

      // Step 2: LLM 生成
      logger.info('Calling LLM service...');
      // Publish state: processing_llm
      await this.publish(`state.${sessionId}`, 'processing_llm', 'text/plain');

      // Use invoke instead of generate (LLMService uses invoke)
      const llmResponse = await this.serviceManager.llm.invoke({
        prompt: transcription,
        task: 'conversation', // Use conversation model
        systemPrompt: "You are a helpful language learning partner. Keep your responses concise and natural for voice conversation.", // Default or from session context
        temperature: 0.7
      });
      
      const responseText = llmResponse.response;
      session.llmResponse = responseText;

      logger.info({ responseText }, 'LLM response completed');

      // 发布 LLM 响应
      await this.publish(`lm.${sessionId}`, responseText, 'text/plain');

      // Step 3: TTS 合成
      logger.info('Calling TTS service...');
      // Publish state: processing_tts
      await this.publish(`state.${sessionId}`, 'processing_tts', 'text/plain');

      const ttsResult = await this.serviceManager.tts.invoke(responseText, {
          voice: 'default', // Should be configurable
          speed: 1.0
      });

      logger.info({ byteLength: ttsResult.audio.byteLength }, 'TTS synthesis completed');

      // 发布 TTS 音频
      await this.publish(`audio.tts.${sessionId}`, ttsResult.audio, 'audio/pcm');

      // Publish state: idle
      await this.publish(`state.${sessionId}`, 'idle', 'text/plain');

      logger.info({ sessionId }, 'Session processing completed');

      // 清理会话
      this.sessionManager.removeSession(sessionId);
    } catch (error) {
      logger.error({ sessionId, error }, 'Session processing failed');

      // 发布错误消息
      const errorMessage = error instanceof Error ? error.message : String(error);
      await this.publish(
        `error.${sessionId}`,
        JSON.stringify({ error: errorMessage }),
        'application/json'
      );
      
      // Publish state: error
      await this.publish(`state.${sessionId}`, 'error', 'text/plain');
    }
  }

  /**
   * 发布消息到软总线
   */
  private async publish(topic: string, data: string | Uint8Array, contentType: string): Promise<void> {
    if (!this.softbusClient) return;

    const payload = typeof data === 'string' ? new TextEncoder().encode(data) : data;

    try {
      await this.softbusClient.publish(topic, payload, contentType);
      console.log(`[VoiceDialogue] 发布消息到主题 [${topic}]:`, payload.byteLength, 'bytes');
    } catch (error) {
      console.error(`[VoiceDialogue] 发布消息失败 [${topic}]:`, error);
    }
  }

  /**
   * 实时流式 ASR（可选）
   */
  private async streamASR(sessionId: string, audioChunk: Uint8Array): Promise<void> {
    // TODO: Implement streaming ASR using this.serviceManager.asr.getInputStream()
    // Currently disabled to avoid compilation errors with missing methods
    /*
    try {
      // 调用流式 ASR（需要 ASR 服务支持）
      const partialTranscription = await asrService.transcribeStream(audioChunk);
      
      if (partialTranscription) {
        // 发布部分转写结果
        await this.publish(
          `text.${sessionId}.partial`,
          partialTranscription,
          'text/plain'
        );
      }
    } catch (error) {
      console.error('[VoiceDialogue] 流式 ASR 失败:', error);
    }
    */
  }

  /**
   * 心跳（可选）
   */
  private startHeartbeat(): void {
    setInterval(() => {
      if (!this.isRunning || !this.softbusClient) return;

      this.softbusClient
        .publish('svc.voice-dialogue.presence', new TextEncoder().encode('alive'), 'text/plain')
        .catch((error) => {
          logger.error({ error }, 'Heartbeat failed');
        });
    }, 30000); // 30 秒
  }
}

