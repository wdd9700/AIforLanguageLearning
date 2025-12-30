/**
 * @fileoverview 查询 API 路由 (Query API Routes)
 * @description
 * 该文件定义了多模态词汇查询相关的 API 路由，统一处理文本、图片 (OCR)、选词和语音 (ASR) 输入。
 * 
 * 主要功能：
 * 1. 文本查询：直接输入单词或短语，调用 LLM 获取释义、发音和例句
 * 2. OCR 查询：上传图片，自动识别文本并进行解释
 * 3. 选词查询：处理前端剪贴板或划词选中的文本
 * 4. 语音查询：上传音频，通过 ASR 转录为文本后进行解释
 * 5. 自动记录：所有查询结果自动保存到学习记录和生词本中
 * 
 * 流程：
 * 输入(文本/图片/语音) -> 预处理(OCR/ASR) -> LLM 解释 -> 结果解析 -> 存库 -> 返回响应
 * 
 * 待改进项：
 * - [ ] 增加高频词汇查询缓存
 * - [ ] 支持多目标语言配置 (目前默认为英语学习)
 * - [ ] 优化外部服务调用失败时的降级处理
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { Router } from 'express';
import { authMiddleware } from '../../middleware/auth';
import { ServiceManager } from '../../managers/service-manager';
import { Database } from '../../database/db';
import { QueryController } from '../../controllers/query.controller';

/**
 * 创建查询路由
 * 
 * @param db 数据库实例
 * @param serviceManager 服务管理器实例
 * @returns Express Router 对象
 */
export function createQueryRoutes(db: Database, serviceManager: ServiceManager): Router {
  const router = Router();
  const queryController = new QueryController(db, serviceManager);

  /**
   * POST /api/query/vocabulary
   * 入口 1: 文本输入查询词汇
   */
  router.post(
    '/vocabulary',
    authMiddleware,
    queryController.queryVocabulary
  );

  /**
   * POST /api/query/ocr
   * 入口 2: 截图 OCR 识别 + 词汇查询
   */
  router.post(
    '/ocr',
    authMiddleware,
    queryController.queryOcr
  );

  /**
   * POST /api/query/selected
   * 入口 3: 选中文本查询（前端通过剪贴板传入）
   */
  router.post(
    '/selected',
    authMiddleware,
    queryController.querySelected
  );

  /**
   * POST /api/query/voice
   * 入口 4: 语音输入 ASR + 词汇查询
   */
  router.post(
    '/voice',
    authMiddleware,
    queryController.queryVoice
  );

  return router;
}
