import { Response, NextFunction } from 'express';
import { AuthRequest } from '../middleware/auth';
import { createError } from '../middleware/error-handler';
import { ServiceManager } from '../managers/service-manager';
import { LearningRecordModel } from '../models/learning-record';
import { VocabularyModel } from '../models/vocabulary';
import { Database } from '../database/db';
import { createLogger } from '../utils/logger';
import { parseLLMJson } from '../utils/json-parser';

const logger = createLogger('QueryController');

export class QueryController {
  private learningRecordModel: LearningRecordModel;
  private vocabularyModel: VocabularyModel;
  private serviceManager: ServiceManager;

  constructor(db: Database, serviceManager: ServiceManager) {
    this.learningRecordModel = new LearningRecordModel(db);
    this.vocabularyModel = new VocabularyModel(db);
    this.serviceManager = serviceManager;
  }

  /**
   * 文本输入查询词汇
   * 
   * 处理用户输入的单词查询请求。
   * 
   * 流程：
   * 1. 验证输入单词。
   * 2. 获取或创建持久化的会话上下文 (sessionId: vocab_{userId})，以支持多轮对话。
   * 3. 构建 LLM 提示词，请求解释单词。
   * 4. 调用 LLM 服务获取解释（当前配置为返回文本格式）。
   * 5. 更新会话历史记录。
   * 6. 构造返回给前端的数据结构。
   * 7. 保存查询记录到 learning_records 表。
   * 8. 将单词及其解释保存到用户的生词本 (vocabulary) 中。
   * 
   * @param req Express 请求对象，包含查询单词 (req.body.word)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public queryVocabulary = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const { word } = req.body;

      if (!word || typeof word !== 'string') {
        throw createError('Invalid word parameter', 400, 'VALIDATION_ERROR');
      }

      const userId = req.userId!;
      const sessionId = `vocab_${userId}`; // Persistent session for vocabulary

      // Get context (do NOT reset)
      const context = await this.serviceManager.context.getContext(sessionId, String(userId));

      // 构建 LLM 提示词
      const prompt = `请解释单词 "${word}"。`;

      // 调用 LLM 服务（使用 'vocabulary' 任务类型以匹配配置）
      const llmResponse = await this.serviceManager.llm.invoke({
        prompt,
        task: 'vocabulary',
        history: context.history, // Pass history
        temperature: 0.3,
        jsonMode: false // Changed to false as the new prompt requests text format
      });

      console.log('--- LLM Raw Response ---');
      console.log(llmResponse.response);
      console.log('------------------------');

      // Update history
      await this.serviceManager.context.addMessage(sessionId, 'user', prompt);
      await this.serviceManager.context.addMessage(sessionId, 'assistant', llmResponse.response);

      let resultData;
      // Since we are now getting text, we wrap it in a structure the frontend can display
      resultData = {
          word: word,
          meaning: llmResponse.response, // Put the whole text in meaning
          pronunciation: '',
          pos: '',
          difficulty: 'General',
          examples: [],
          synonyms: []
      };

      // 保存学习记录
      await this.learningRecordModel.create({
        userId,
        type: 'vocabulary',
        content: word,
        metadata: {
          result: resultData,
          tokenUsage: llmResponse.tokenUsage,
        },
      });

      // 保存到生词本
      await this.vocabularyModel.addWord(userId, word, {
          definition: resultData.meaning,
          pronunciation: resultData.pronunciation,
          example: resultData.examples?.[0] || ''
      });

      logger.info({ userId, word }, 'Vocabulary query completed');

      res.json({
        success: true,
        data: resultData,
      });
    } catch (error: any) {
      next(error);
    }
  };

  /**
   * 截图 OCR 识别 + 词汇查询
   * 
   * 处理用户上传的图片，进行 OCR 文字识别，并对识别出的文本进行解释。
   * 
   * 流程：
   * 1. 验证上传的图片数据 (Base64)。
   * 2. 调用 OCR 服务识别图片中的文字。
   * 3. 如果识别到文字，构建 LLM 提示词请求解释。
   * 4. 调用 LLM 服务获取解释（JSON 格式）。
   * 5. 解析 LLM 返回的 JSON 数据。
   * 6. 保存识别和查询记录到 learning_records 表，记录来源为 'ocr'。
   * 7. 返回识别到的文本、置信度及解释。
   * 
   * @param req Express 请求对象，包含图片数据 (req.body.image)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public queryOcr = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const { image } = req.body;

      if (!image || typeof image !== 'string') {
        throw createError('Invalid image parameter', 400, 'VALIDATION_ERROR');
      }

      const userId = req.userId!;

      // 调用 OCR 服务
      const ocrResponse = await this.serviceManager.ocr.invoke(image);

      if (!ocrResponse.text) {
        throw createError('No text detected in image', 400, 'OCR_NO_TEXT');
      }

      // 构建 LLM 提示词
      const prompt = `请解释以下文本中的词汇或短语：${ocrResponse.text}`;

      // 调用 LLM 服务
      const llmResponse = await this.serviceManager.llm.invoke({
        prompt,
        task: 'vocabulary',
        jsonMode: true
      });

      let explanationData;
      try {
          explanationData = parseLLMJson(llmResponse.response);
      } catch (e) {
          logger.warn({ error: e }, 'Failed to parse OCR vocabulary JSON');
          explanationData = { meaning: llmResponse.response };
      }

      // 保存学习记录
      await this.learningRecordModel.create({
        userId,
        type: 'vocabulary',
        content: ocrResponse.text,
        metadata: {
          source: 'ocr',
          confidence: ocrResponse.confidence,
          response: explanationData,
          tokenUsage: llmResponse.tokenUsage,
        },
      });

      logger.info({ userId, text: ocrResponse.text }, 'OCR vocabulary query completed');

      res.json({
        success: true,
        data: {
          detectedText: ocrResponse.text,
          confidence: ocrResponse.confidence,
          explanation: explanationData,
        },
      });
    } catch (error: any) {
      next(error);
    }
  };

  /**
   * 选中文本查询
   * 
   * 处理用户在前端选中的文本（如通过划词或剪贴板获取），并进行解释。
   * 
   * 流程：
   * 1. 验证输入的文本。
   * 2. 构建 LLM 提示词请求解释。
   * 3. 调用 LLM 服务获取解释（JSON 格式）。
   * 4. 解析 LLM 返回的 JSON 数据。
   * 5. 保存查询记录到 learning_records 表，记录来源为 'selected'。
   * 6. 返回文本及解释。
   * 
   * @param req Express 请求对象，包含选中文本 (req.body.text)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public querySelected = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const { text } = req.body;

      if (!text || typeof text !== 'string') {
        throw createError('Invalid text parameter', 400, 'VALIDATION_ERROR');
      }

      const userId = req.userId!;

      // 构建 LLM 提示词
      const prompt = `请解释以下选中的文本：${text}`;

      // 调用 LLM 服务
      const llmResponse = await this.serviceManager.llm.invoke({
        prompt,
        task: 'vocabulary',
        jsonMode: true
      });

      let explanationData;
      try {
          explanationData = parseLLMJson(llmResponse.response);
      } catch (e) {
          logger.warn({ error: e }, 'Failed to parse Selected vocabulary JSON');
          explanationData = { meaning: llmResponse.response };
      }

      // 保存学习记录
      await this.learningRecordModel.create({
        userId,
        type: 'vocabulary',
        content: text,
        metadata: {
          source: 'selected',
          response: explanationData,
          tokenUsage: llmResponse.tokenUsage,
        },
      });

      logger.info({ userId, text }, 'Selected text query completed');

      res.json({
        success: true,
        data: {
          text,
          explanation: explanationData,
        },
      });
    } catch (error: any) {
      next(error);
    }
  };

  /**
   * 语音输入 ASR + 词汇查询
   * 
   * 处理用户上传的语音数据，进行 ASR 语音识别，并对识别出的文本进行解释。
   * 
   * 流程：
   * 1. 验证上传的音频数据 (Base64)。
   * 2. 将 Base64 音频转换为 Buffer。
   * 3. 调用 ASR 服务识别语音内容。
   * 4. 如果识别到文字，构建 LLM 提示词请求解释。
   * 5. 调用 LLM 服务获取解释（JSON 格式）。
   * 6. 解析 LLM 返回的 JSON 数据。
   * 7. 保存识别和查询记录到 learning_records 表，记录来源为 'voice'。
   * 8. 返回识别到的文本及解释。
   * 
   * @param req Express 请求对象，包含音频数据 (req.body.audio)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public queryVoice = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const { audio } = req.body;

      if (!audio || typeof audio !== 'string') {
        throw createError('Invalid audio parameter', 400, 'VALIDATION_ERROR');
      }

      const userId = req.userId!;

      // 将 Base64 音频转换为 Buffer
      const audioBuffer = Buffer.from(audio, 'base64');

      // 调用 ASR 服务
      const asrResponse = await this.serviceManager.asr.invoke(audioBuffer);

      if (!asrResponse.text) {
        throw createError('No text detected in audio', 400, 'ASR_NO_TEXT');
      }

      // 构建 LLM 提示词
      const prompt = `请解释以下语音识别的文本：${asrResponse.text}`;

      // 调用 LLM 服务
      const llmResponse = await this.serviceManager.llm.invoke({
        prompt,
        task: 'vocabulary',
        jsonMode: true
      });

      let explanationData;
      try {
          explanationData = parseLLMJson(llmResponse.response);
      } catch (e) {
          logger.warn({ error: e }, 'Failed to parse Voice vocabulary JSON');
          explanationData = { meaning: llmResponse.response };
      }

      // 保存学习记录
      await this.learningRecordModel.create({
        userId,
        type: 'vocabulary',
        content: asrResponse.text,
        metadata: {
          source: 'voice',
          response: explanationData,
          tokenUsage: llmResponse.tokenUsage,
        },
      });

      logger.info({ userId, text: asrResponse.text }, 'Voice query completed');

      res.json({
        success: true,
        data: {
          detectedText: asrResponse.text,
          explanation: explanationData,
        },
      });
    } catch (error: any) {
      next(error);
    }
  };
}
