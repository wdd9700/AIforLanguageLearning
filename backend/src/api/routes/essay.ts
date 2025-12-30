/**
 * @fileoverview 作文批改 API 路由 (Essay API Routes)
 * @description
 * 该文件定义了作文批改相关的 API 路由，支持文本和图片输入，集成 OCR 和 LLM 服务进行智能批改。
 * 
 * 主要功能：
 * 1. 智能批改：接收作文内容（文本或图片），调用 LLM 进行多维度评分和点评
 * 2. OCR 集成：自动识别上传图片中的手写或打印文本
 * 3. 结果解析：解析 LLM 返回的结构化 JSON 数据（分数、评语、纠错）
 * 4. 记录保存：将原始作文、批改结果和评分保存到数据库（LearningRecord 和 Essay 表）
 * 
 * 流程：
 * 1. 接收请求 -> 2. (可选) OCR 识别 -> 3. 构建 Prompt -> 4. 调用 LLM -> 5. 解析结果 -> 6. 存库 -> 7. 返回响应
 * 
 * 待改进项：
 * - [ ] 引入任务队列 (Job Queue) 处理长文本或高并发请求
 * - [ ] 优化 Prompt 以获得更稳定的 JSON 输出结构
 * - [ ] 增加作文修改历史版本管理
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { Router } from 'express';
import { authMiddleware } from '../../middleware/auth';
import { ServiceManager } from '../../managers/service-manager';
import { Database } from '../../database/db';
import { EssayController } from '../../controllers/essay.controller';

/**
 * 创建作文批改路由
 * 
 * @param db 数据库实例
 * @param serviceManager 服务管理器实例，用于调用 OCR 和 LLM 服务
 * @returns Express Router 对象
 */
export function createEssayRoutes(db: Database, serviceManager: ServiceManager): Router {
  const router = Router();
  const essayController = new EssayController(db, serviceManager);

  /**
   * POST /api/essay/correct
   * 作文批改接口
   */
  router.post(
    '/correct',
    authMiddleware,
    essayController.correct
  );

  /**
   * POST /api/essay/ocr-correct
   * OCR 识别 + 作文批改接口 (Legacy)
   */
  router.post(
    '/ocr-correct',
    authMiddleware,
    essayController.ocrCorrect
  );

  return router;
}
