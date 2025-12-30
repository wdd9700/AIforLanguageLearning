import { Response, NextFunction } from 'express';
import { AuthRequest } from '../middleware/auth';
import { createError } from '../middleware/error-handler';
import { ServiceManager } from '../managers/service-manager';
import { createLogger } from '../utils/logger';

const logger = createLogger('VoiceController');

export class VoiceController {
  private serviceManager: ServiceManager;

  constructor(serviceManager: ServiceManager) {
    this.serviceManager = serviceManager;
  }

  /**
   * 生成系统提示词 (System Prompt)
   * 
   * 使用 "思考模型" (Thinking Model, 如 qwen3-4b-thinking) 将用户提供的简短场景描述扩展为详细的角色扮演系统提示词。
   * 生成的提示词会被缓存到当前用户的语音会话上下文 (metadata) 中，供后续对话使用。
   * 
   * @param req Express 请求对象，包含场景描述 (req.body.scenario) 和目标语言 (req.body.language)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public generatePrompt = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const { scenario, language } = req.body;
      if (!scenario) throw createError('Scenario is required', 400, 'VALIDATION_ERROR');

      const targetLang = language || 'English';
      
      // Use PromptManager to render the expansion prompt
      const prompt = await this.serviceManager.prompt.render('analysis/prompt_expansion', {
        scenario,
        targetLang
      });

      // Call LLM (Thinking Model) via 'prompt_expansion' task
      const llmResponse = await this.serviceManager.llm.invoke({
        prompt,
        task: 'prompt_expansion', // Routes to qwen3-4b-thinking
        temperature: 0.7,
      });

      const generatedSystemPrompt = llmResponse.response.trim();

      // Cache this system prompt in the session context for future use
      // We use a temporary session ID for this generation flow or the user's current session
      const userId = req.userId!;
      const sessionId = `voice_${userId}_current`; // Fixed session ID for the active voice chat
      
      // Reset context for new scenario
      const context = await this.serviceManager.context.resetContext(sessionId, String(userId));
      
      // Store the new system prompt in metadata
      context.metadata.systemPrompt = generatedSystemPrompt;
      await this.serviceManager.context.saveContext(context);

      res.json({
        success: true,
        systemPrompt: generatedSystemPrompt
      });

    } catch (error) {
      next(error);
    }
  };

  /**
   * 开启语音会话
   * 
   * 初始化语音对话会话。
   * 1. 获取之前生成或传入的系统提示词 (System Prompt)。
   * 2. 使用 "对话模型" (Dialogue Model, 如 qwen3-vl-8b) 生成开场白。
   * 3. 将开场白添加到会话历史中。
   * 4. 调用 TTS 服务将开场白转换为语音。
   * 5. 返回开场白文本和音频数据 (Base64)。
   * 
   * @param req Express 请求对象，可选包含系统提示词 (req.body.systemPrompt)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public startSession = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const userId = req.userId!;
      const sessionId = `voice_${userId}_current`;
      
      // Retrieve context to get the stored system prompt
      const context = await this.serviceManager.context.getContext(sessionId, String(userId));
      const systemPrompt = context.metadata.systemPrompt || req.body.systemPrompt;

      if (!systemPrompt) throw createError('System Prompt is required', 400, 'VALIDATION_ERROR');

      // Update metadata if provided in body (fallback)
      if (req.body.systemPrompt) {
          context.metadata.systemPrompt = req.body.systemPrompt;
          await this.serviceManager.context.saveContext(context);
      }

      // Generate Opening Line
      // We don't add this to history yet, or we can add it as assistant message
      const llmResponse = await this.serviceManager.llm.invoke({
        prompt: "(Generate the first opening line for this roleplay to start the conversation. Keep it short and engaging.)",
        task: 'conversation',
        systemPrompt: systemPrompt, // Pass the specific system prompt
        temperature: 0.7,
      });

      const openingText = llmResponse.response.trim();
      
      // Add to context history
      await this.serviceManager.context.addMessage(sessionId, 'assistant', openingText);

      // Generate Audio for Opening Line
      const ttsResult = await this.serviceManager.tts.invoke(openingText, {
        voice: 'default',
        speed: 1.0
      });

      res.json({
        success: true,
        openingText,
        openingAudio: ttsResult.audio.toString('base64')
      });

    } catch (error) {
      next(error);
    }
  };
}
