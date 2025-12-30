import { Response, NextFunction } from 'express';
import { AuthRequest } from '../middleware/auth';
import { createError } from '../middleware/error-handler';
import { ServiceManager } from '../managers/service-manager';
import { LearningRecordModel } from '../models/learning-record';
import { StudentModel } from '../models/student';
import { VocabularyModel } from '../models/vocabulary';
import { EssayModel } from '../models/essay';
import { Database } from '../database/db';
import { createLogger } from '../utils/logger';
import { parseLLMJson } from '../utils/json-parser';

const logger = createLogger('LearningController');

export class LearningController {
  private learningRecordModel: LearningRecordModel;
  private studentModel: StudentModel;
  private vocabularyModel: VocabularyModel;
  private essayModel: EssayModel;
  private serviceManager: ServiceManager;

  constructor(db: Database, serviceManager: ServiceManager) {
    this.learningRecordModel = new LearningRecordModel(db);
    this.studentModel = new StudentModel(db);
    this.vocabularyModel = new VocabularyModel(db);
    this.essayModel = new EssayModel(db);
    this.serviceManager = serviceManager;
  }

  /**
   * 获取学生档案信息
   * 
   * 根据当前登录用户的ID获取其学生档案。
   * 如果档案不存在，系统会自动创建一个空的档案并返回。
   * 
   * @param req Express 请求对象，包含认证用户信息 (req.userId)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public getProfile = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const userId = req.userId!;
      let profile = await this.studentModel.getProfile(userId);
      if (!profile) {
        // Auto-create if not exists
        await this.studentModel.updateProfile(userId, {});
        profile = await this.studentModel.getProfile(userId);
      }
      res.json({ success: true, data: profile });
    } catch (e) { next(e); }
  };

  /**
   * 更新学生档案信息
   * 
   * 根据请求体中的数据更新当前登录用户的学生档案。
   * 支持部分更新，仅更新请求中提供的字段。
   * 
   * @param req Express 请求对象，包含认证用户信息 (req.userId) 和要更新的档案数据 (req.body)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public updateProfile = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const userId = req.userId!;
      await this.studentModel.updateProfile(userId, req.body);
      res.json({ success: true });
    } catch (e) { next(e); }
  };

  /**
   * 获取待复习生词列表
   * 
   * 查询当前用户所有已到复习时间的生词。
   * 基于间隔重复算法（Spaced Repetition）确定哪些单词需要复习。
   * 
   * @param req Express 请求对象，包含认证用户信息 (req.userId)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public getDueVocabulary = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const userId = req.userId!;
      const words = await this.vocabularyModel.getDueWords(userId);
      res.json({ success: true, data: words });
    } catch (e) { next(e); }
  };

  /**
   * 更新生词掌握情况（复习打卡）
   * 
   * 根据用户对生词的复习结果（认识/不认识），更新该生词的掌握程度和下次复习时间。
   * 
   * @param req Express 请求对象，包含生词ID (req.params.id) 和复习结果 (req.body.correct)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public reviewVocabulary = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const { correct } = req.body;
      await this.vocabularyModel.updateMastery(parseInt(req.params.id), correct);
      res.json({ success: true });
    } catch (e) { next(e); }
  };

  /**
   * 获取作文历史记录
   * 
   * 查询当前用户提交的所有作文及其批改记录。
   * 
   * @param req Express 请求对象，包含认证用户信息 (req.userId)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public getEssays = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const userId = req.userId!;
      const essays = await this.essayModel.getHistory(userId);
      res.json({ success: true, data: essays });
    } catch (e) { next(e); }
  };

  /**
   * 获取通用学习记录
   * 
   * 查询用户的学习活动记录。支持按类型筛选（如 'vocabulary', 'essay', 'dialogue'）和限制返回数量。
   * 返回的数据包含记录ID、类型、内容摘要、元数据（已解析的JSON）和创建时间。
   * 
   * @param req Express 请求对象，包含查询参数 type (可选) 和 limit (可选)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public getRecords = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const userId = req.userId!;
      const { type, limit } = req.query;

      let records;
      if (type && typeof type === 'string') {
        records = await this.learningRecordModel.getByUserAndType(
          userId,
          type as any,
          limit ? parseInt(limit as string) : 50
        );
      } else {
        records = await this.learningRecordModel.getByUser(
          userId,
          limit ? parseInt(limit as string) : 100
        );
      }

      res.json({
        success: true,
        data: {
          records: records.map((record) => ({
            id: record.id,
            type: record.type,
            content: record.content,
            metadata: record.metadata ? JSON.parse(record.metadata) : null,
            createdAt: record.created_at,
          })),
        },
      });
    } catch (error: any) {
      next(error);
    }
  };

  /**
   * 获取学习统计数据
   * 
   * 统计用户在各个模块（生词、作文、对话、分析）的学习记录数量。
   * 返回各类别的计数以及总数。
   * 
   * @param req Express 请求对象，包含认证用户信息 (req.userId)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public getStats = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const userId = req.userId!;

      // 统计各类型记录数量
      const vocabularyCount = await this.learningRecordModel.countByUserAndType(userId, 'vocabulary');
      const essayCount = await this.learningRecordModel.countByUserAndType(userId, 'essay');
      const dialogueCount = await this.learningRecordModel.countByUserAndType(userId, 'dialogue');
      const analysisCount = await this.learningRecordModel.countByUserAndType(userId, 'analysis');

      res.json({
        success: true,
        data: {
          vocabulary: vocabularyCount,
          essay: essayCount,
          dialogue: dialogueCount,
          analysis: analysisCount,
          total: vocabularyCount + essayCount + dialogueCount + analysisCount,
        },
      });
    } catch (error: any) {
      next(error);
    }
  };

  /**
   * 生成学习分析报告
   * 
   * 基于用户最近的学习记录，调用 LLM 生成指定维度的学习分析报告。
   * 
   * 流程：
   * 1. 验证请求参数 dimension。
   * 2. 获取用户最近的 100 条学习记录。
   * 3. 使用 PromptManager 构建提示词，包含分析维度和记录摘要。
   * 4. 记录审计日志 (start_analysis)。
   * 5. 调用 LLM 服务进行分析，要求返回 JSON 格式。
   * 6. 解析 LLM 返回的 JSON 数据，如果解析失败则进行回退处理。
   * 7. 将分析结果保存到 learning_records 表中，类型为 'analysis'。
   * 8. 返回分析结果。
   * 
   * @param req Express 请求对象，包含分析维度 (req.body.dimension)
   * @param res Express 响应对象
   * @param next Express 下一步中间件函数
   */
  public analyze = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      const userId = req.userId!;
      const { dimension } = req.body;

      if (!dimension || typeof dimension !== 'string') {
        throw createError('Invalid dimension parameter', 400, 'VALIDATION_ERROR');
      }

      // 获取用户最近的学习记录
      const records = await this.learningRecordModel.getByUser(userId, 100);

      const recordsSummary = records
        .map((r) => `${r.type}: ${r.content.substring(0, 100)}`)
        .join('\n');

      // 使用 PromptManager 构建提示词
      const prompt = await this.serviceManager.prompt.render('analysis/learning_report', {
        dimension,
        recordsSummary
      });

      // 记录审计日志
      const sessionId = `analysis_${userId}_${Date.now()}`;
      await this.serviceManager.context.logAudit(sessionId, 'start_analysis', { dimension, recordCount: records.length });

      // 调用 LLM 服务
      const llmResponse = await this.serviceManager.llm.invoke({
        prompt,
        task: 'analysis', // 使用配置中定义的 'analysis' 任务，对应 qwen3-4b-thinking
        maxTokens: 1500,
        temperature: 0.3,
        jsonMode: true
      });

      let resultData;
      try {
          resultData = parseLLMJson(llmResponse.response);
      } catch (e) {
          logger.warn({ error: e }, 'Failed to parse Learning Analysis JSON');
          resultData = {
              score: 0,
              insights: [llmResponse.response] // 回退：将全文作为一条洞察
          };
      }

      // 保存分析记录
      await this.learningRecordModel.create({
        userId,
        type: 'analysis',
        content: dimension,
        metadata: {
          analysis: resultData, // 保存结构化数据
          recordCount: records.length,
          tokenUsage: llmResponse.tokenUsage,
        },
      });

      logger.info({ userId, dimension }, 'Learning analysis completed');

      res.json({
        success: true,
        data: {
          dimension,
          ...resultData
        },
      });
    } catch (error: any) {
      next(error);
    }
  };
}
