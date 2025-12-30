/**
 * @fileoverview 学习记录数据模型 (Learning Record Model)
 * @description
 * 该文件定义了通用学习记录 (Learning Record) 的数据结构和数据库操作方法。
 * 
 * 主要功能：
 * 1. 数据结构：定义 LearningRecord 接口，支持多种类型 (vocabulary, essay, dialogue, analysis)
 * 2. 统一存储：将不同类型的学习活动统一存储在 learning_records 表中，使用 metadata 字段存储差异化数据
 * 3. 记录创建：保存用户的学习行为和 AI 生成的反馈
 * 4. 查询统计：支持按类型、按用户查询记录，以及统计各类记录的数量
 * 
 * 数据库表：learning_records
 * 
 * 待改进项：
 * - [ ] 增加数据归档机制，定期迁移冷数据
 * - [ ] 优化批量插入性能
 * - [ ] 创建预聚合表以加速统计查询
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { Database } from '../database/db';
import { createLogger } from '../utils/logger';

const logger = createLogger('LearningRecordModel');

/**
 * 学习记录接口
 * 对应数据库中的 learning_records 表结构
 */
export interface LearningRecord {
  id: number;
  user_id: number;
  type: 'vocabulary' | 'essay' | 'dialogue' | 'analysis';
  content: string;
  metadata: string; // JSON string
  created_at: number;
}

/**
 * 创建学习记录参数接口
 */
export interface CreateLearningRecordParams {
  userId: number;
  type: LearningRecord['type'];
  content: string;
  metadata?: any;
}

/**
 * 学习记录模型类
 * 提供对学习记录表的 CRUD 操作
 */
export class LearningRecordModel {
  constructor(private db: Database) {}

  /**
   * 创建新的学习记录
   * 
   * @param params 创建参数，包含用户ID、类型、内容和元数据
   * @returns 创建成功的学习记录对象
   */
  async create(params: CreateLearningRecordParams): Promise<LearningRecord> {
    const { userId, type, content, metadata } = params;

    const now = Date.now();
    const metadataJson = metadata ? JSON.stringify(metadata) : null;

    const recordId = await this.db.insert(
      `INSERT INTO learning_records (user_id, type, content, metadata, created_at)
       VALUES (?, ?, ?, ?, ?)`,
      [userId, type, content, metadataJson, now]
    );

    logger.info({ recordId, userId, type }, 'Learning record created');

    return {
      id: recordId,
      user_id: userId,
      type,
      content,
      metadata: metadataJson || '',
      created_at: now,
    };
  }

  /**
   * 获取用户的特定类型学习记录
   * 按创建时间倒序排列
   * 
   * @param userId 用户ID
   * @param type 记录类型
   * @param limit 返回记录数量限制，默认 50
   * @returns 学习记录列表
   */
  async getByUserAndType(
    userId: number,
    type: LearningRecord['type'],
    limit: number = 50
  ): Promise<LearningRecord[]> {
    return this.db.all<LearningRecord>(
      `SELECT * FROM learning_records 
       WHERE user_id = ? AND type = ? 
       ORDER BY created_at DESC 
       LIMIT ?`,
      [userId, type, limit]
    );
  }

  /**
   * 获取用户的所有学习记录
   * 按创建时间倒序排列
   * 
   * @param userId 用户ID
   * @param limit 返回记录数量限制，默认 100
   * @returns 学习记录列表
   */
  async getByUser(userId: number, limit: number = 100): Promise<LearningRecord[]> {
    return this.db.all<LearningRecord>(
      `SELECT * FROM learning_records 
       WHERE user_id = ? 
       ORDER BY created_at DESC 
       LIMIT ?`,
      [userId, limit]
    );
  }

  /**
   * 统计用户某类型记录的数量
   * 
   * @param userId 用户ID
   * @param type 记录类型
   * @returns 记录总数
   */
  async countByUserAndType(userId: number, type: LearningRecord['type']): Promise<number> {
    const result = await this.db.get<{ count: number }>(
      'SELECT COUNT(*) as count FROM learning_records WHERE user_id = ? AND type = ?',
      [userId, type]
    );

    return result?.count || 0;
  }

  /**
   * 删除单条学习记录
   * 仅允许删除属于该用户的记录
   * 
   * @param recordId 记录ID
   * @param userId 用户ID
   */
  async delete(recordId: number, userId: number): Promise<void> {
    await this.db.run('DELETE FROM learning_records WHERE id = ? AND user_id = ?', [
      recordId,
      userId,
    ]);

    logger.info({ recordId, userId }, 'Learning record deleted');
  }

  /**
   * 删除用户的所有学习记录
   * 通常用于注销账号时的清理
   * 
   * @param userId 用户ID
   */
  async deleteByUser(userId: number): Promise<void> {
    await this.db.run('DELETE FROM learning_records WHERE user_id = ?', [userId]);
    logger.info({ userId }, 'All learning records deleted for user');
  }
}
