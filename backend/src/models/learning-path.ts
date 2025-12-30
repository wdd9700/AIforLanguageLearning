/**
 * @fileoverview 学习路径数据模型 (Learning Path Model)
 * @description
 * 该文件定义了学习路径 (Learning Path) 的数据结构和数据库操作方法。
 * 
 * 主要功能：
 * 1. 数据结构：定义 LearningPath 接口，包含标题、描述、里程碑 (Milestones)、状态和进度
 * 2. 路径创建：为用户生成新的个性化学习计划
 * 3. 活跃路径查询：获取用户当前正在进行的学习路径
 * 4. 进度更新：更新学习路径的完成百分比
 * 
 * 数据库表：learning_paths
 * 
 * 待改进项：
 * - [ ] 实现基于进度的动态路径调整算法
 * - [ ] 支持同时进行多个学习路径
 * - [ ] 对接 CEFR 等国际标准进行难度分级
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { Database } from '../database/db';

export interface LearningPath {
  id: number;
  user_id: number;
  title: string;
  description: string;
  milestones: any[];
  status: 'active' | 'completed' | 'archived';
  progress: number;
  created_at: number;
  updated_at: number;
}

export class LearningPathModel {
  constructor(private db: Database) {}

  /**
   * 创建新的学习路径
   */
  async create(userId: number, title: string, description: string, milestones: any[]): Promise<number> {
    const now = Date.now();
    return await this.db.insert(
      `INSERT INTO learning_paths (user_id, title, description, milestones, status, progress, created_at, updated_at)
       VALUES (?, ?, ?, ?, 'active', 0, ?, ?)`,
      [userId, title, description, JSON.stringify(milestones), now, now]
    );
  }

  /**
   * 获取用户当前活跃的学习路径
   */
  async getActivePath(userId: number): Promise<LearningPath | null> {
    const row = await this.db.get(
      "SELECT * FROM learning_paths WHERE user_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
      [userId]
    );
    if (!row) return null;
    return {
        ...row,
        milestones: row.milestones ? JSON.parse(row.milestones) : []
    };
  }

  /**
   * 更新学习进度
   */
  async updateProgress(id: number, progress: number): Promise<void> {
    await this.db.run(
        'UPDATE learning_paths SET progress = ?, updated_at = ? WHERE id = ?',
        [progress, Date.now(), id]
    );
  }
}
