/**
 * @fileoverview 作文批改控制器 (Essay Controller)
 * @description
 * 处理作文批改相关的业务逻辑。
 * 
 * 主要功能：
 * 1. 作文批改 (Correct)：
 *    - 支持纯文本输入或图片输入 (自动调用 OCR)。
 *    - 调用 LLM 服务进行多维度评分 (词汇、语法、逻辑等) 和生成评语。
 *    - 自动保存批改记录到数据库。
 * 2. 历史记录查询 (GetHistory)：获取用户的作文批改历史。
 * 3. 详情查询 (GetById)：获取单篇作文的详细批改结果。
 */

import { Response, NextFunction } from 'express';
import { AuthRequest } from '../middleware/auth';
import { createError } from '../middleware/error-handler';
import { ServiceManager } from '../managers/service-manager';
import { LearningRecordModel } from '../models/learning-record';
import { EssayModel } from '../models/essay';
import { Database } from '../database/db';
import { createLogger } from '../utils/logger';
import { parseLLMJson } from '../utils/json-parser';

const logger = createLogger('EssayController');

export class EssayController {
  private learningRecordModel: LearningRecordModel;
  private essayModel: EssayModel;
  private serviceManager: ServiceManager;

  constructor(db: Database, serviceManager: ServiceManager) {
    this.learningRecordModel = new LearningRecordModel(db);
    this.essayModel = new EssayModel(db);
    this.serviceManager = serviceManager;
  }

  /**
   * 处理作文批改请求
   * 
   * 1. 接收文本或图片数据。
   * 2. 如果是图片，调用 OCR 服务提取文本。
   * 3. 调用 LLM 服务进行批改，要求返回 JSON 格式的评分和建议。
   * 4. 将批改结果保存到 essays 表和 learning_records 表。
   * 5. 返回结构化的批改报告。
   */
  public correct = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      let { text, language, image } = req.body;

      // 如果提供了图片，先执行 OCR
      if (image) {
          try {
              const ocrResult = await this.serviceManager.ocr.invoke(image);
              text = ocrResult.text;
              logger.info({ textLength: text?.length }, 'OCR 识别完成');
          } catch (err) {
              logger.error({ err }, 'OCR 识别失败');
              throw createError('OCR 处理失败', 500, 'OCR_ERROR');
          }
      }

      if (!text || typeof text !== 'string') {
        throw createError('无效的文本参数', 400, 'VALIDATION_ERROR');
      }

      const userId = req.userId!;

      // 重置上下文以进行新的作文批改
      const sessionId = `essay_${userId}_${Date.now()}`;
      await this.serviceManager.context.resetContext(sessionId, String(userId));
      await this.serviceManager.context.logAudit(sessionId, 'start_correction', { textLength: text.length });

      // Use PromptManager
      const prompt = await this.serviceManager.prompt.render('essay/correction', {
        language: language || 'English',
        text
      });

      // 调用 LLM 服务
      const llmResponse = await this.serviceManager.llm.invoke({
        prompt,
        task: 'essay_correction',
        maxTokens: 2000,
        temperature: 0.3, // 降低温度以保证 JSON 格式稳定
        jsonMode: true
      });

      let resultData;
      try {
          resultData = parseLLMJson(llmResponse.response);
      } catch (e) {
          logger.warn({ error: e, response: llmResponse.response }, 'Failed to parse LLM JSON response');
          // 回退：将文本作为 feedback
          resultData = {
              scores: { vocabulary: 0, grammar: 0, fluency: 0, logic: 0, content: 0, structure: 0, total: 0 },
              feedback: llmResponse.response,
              correction: '',
              suggestions: [],
              questions: [],
              improvements: [],
              evaluation: ''
          };
      }

      // 保存学习记录
      await this.learningRecordModel.create({
        userId,
        type: 'essay',
        content: text,
        metadata: {
          language: language || 'english',
          correction: resultData.correction || '',
          scores: resultData.scores,
          feedback: resultData.feedback,
          tokenUsage: llmResponse.tokenUsage,
        },
      });

      // 保存到专用作文表
      await this.essayModel.create(
          userId,
          text,
          resultData.correction || '',
          resultData.scores,
          '无标题作文' // TODO: 根据内容自动生成标题
      );

      logger.info({ userId, textLength: text.length }, '作文批改完成');

      res.json({
        success: true,
        data: {
          originalText: text,
          ...resultData
        },
      });
    } catch (error: any) {
      next(error);
    }
  };

  /**
   * OCR 识别 + 作文批改 (旧接口，建议使用 correct 接口统一处理)
   */
  public ocrCorrect = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const { image, language } = req.body;

      if (!image || typeof image !== 'string') {
        throw createError('无效的图片参数', 400, 'VALIDATION_ERROR');
      }

      const userId = req.userId!;

      // 调用 OCR 服务
      const ocrResponse = await this.serviceManager.ocr.invoke(image);

      if (!ocrResponse.text) {
        throw createError('未在图片中检测到文本', 400, 'OCR_NO_TEXT');
      }

      // 构建 LLM 提示词
      const prompt = `请批改以下${language || '英语'}作文，指出语法错误、用词不当、表达不地道的地方，并给出改进建议：\n\n${ocrResponse.text}`;

      // 调用 LLM 服务
      const llmResponse = await this.serviceManager.llm.invoke({
        prompt,
        task: 'essay_correction',
        maxTokens: 2000,
      });

      // 保存学习记录
      await this.learningRecordModel.create({
        userId,
        type: 'essay',
        content: ocrResponse.text,
        metadata: {
          source: 'ocr',
          language: language || 'english',
          confidence: ocrResponse.confidence,
          correction: llmResponse.response,
          tokenUsage: llmResponse.tokenUsage,
        },
      });

      logger.info({ userId, textLength: ocrResponse.text.length }, 'OCR essay correction completed');

      res.json({
        success: true,
        data: {
          detectedText: ocrResponse.text,
          confidence: ocrResponse.confidence,
          correction: llmResponse.response,
        },
      });
    } catch (error: any) {
      next(error);
    }
  };
}
