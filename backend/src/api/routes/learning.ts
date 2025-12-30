/**
 * @fileoverview 学习分析 API 路由 (Learning API Routes)
 * @description
 * 该文件定义了学习管理相关的 API 路由，涵盖学生档案、生词复习、作文历史和智能学习分析。
 * 
 * 主要功能：
 * 1. 学生档案：获取和更新学生的个人学习资料
 * 2. 生词本管理：基于间隔重复算法 (SRS) 获取待复习单词，提交复习结果
 * 3. 作文历史：查询用户的历史作文记录
 * 4. 学习记录：通用查询接口，支持按类型（生词、作文、对话等）筛选
 * 5. 统计数据：提供各类学习活动的数量统计
 * 6. 智能分析：调用 LLM 分析用户近期的学习记录，生成特定维度（如语法、词汇量）的评估报告
 * 
 * 待改进项：
 * - [ ] 为统计数据接口增加缓存机制 (Redis/Memory)
 * - [ ] 支持导出学习记录 (PDF/CSV)
 * - [ ] 细化分析维度，支持自定义时间范围
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { Router } from 'express';
import { authMiddleware } from '../../middleware/auth';
import { ServiceManager } from '../../managers/service-manager';
import { Database } from '../../database/db';
import { LearningController } from '../../controllers/learning.controller';

/**
 * 创建学习分析路由
 * 
 * @param db 数据库实例
 * @param serviceManager 服务管理器实例
 * @returns Express Router 对象
 */
export function createLearningRoutes(db: Database, serviceManager: ServiceManager): Router {
  const router = Router();
  const learningController = new LearningController(db, serviceManager);

  /**
   * GET /api/learning/profile
   * 获取学生档案
   */
  router.get('/profile', authMiddleware, learningController.getProfile);

  /**
   * POST /api/learning/profile
   * 更新学生档案
   */
  router.post('/profile', authMiddleware, learningController.updateProfile);

  /**
   * GET /api/learning/vocabulary/due
   * 获取待复习生词
   */
  router.get('/vocabulary/due', authMiddleware, learningController.getDueVocabulary);

  /**
   * POST /api/learning/vocabulary/:id/review
   * 更新生词掌握情况
   */
  router.post('/vocabulary/:id/review', authMiddleware, learningController.reviewVocabulary);

  /**
   * GET /api/learning/essays
   * 获取作文历史记录
   */
  router.get('/essays', authMiddleware, learningController.getEssays);

  /**
   * GET /api/learning/records
   * 获取通用学习记录
   */
  router.get(
    '/records',
    authMiddleware,
    learningController.getRecords
  );

  /**
   * GET /api/learning/stats
   * 获取学习统计数据
   */
  router.get(
    '/stats',
    authMiddleware,
    learningController.getStats
  );

  /**
   * POST /api/learning/analyze
   * 生成学习分析报告
   */
  router.post(
    '/analyze',
    authMiddleware,
    learningController.analyze
  );

  return router;
}
