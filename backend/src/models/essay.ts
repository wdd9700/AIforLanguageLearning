/**
 * @fileoverview 作文数据模型 (Essay Model)
 * @description
 * 该文件定义了作文 (Essay) 的数据结构和数据库操作方法。
 * 
 * 主要功能：
 * 1. 数据结构：定义 Essay 接口，包含原文、批改后文本、评分详情 (JSON) 等字段
 * 2. 创建记录：将用户提交的作文及 LLM 生成的批改结果保存到数据库
 * 3. 历史查询：支持分页查询特定用户的作文历史
 * 4. 详情获取：根据 ID 获取单篇作文的完整信息
 * 
 * 数据库表：essays
 * 
 * 待改进项：
 * - [ ] 增加全文检索 (FTS) 支持，便于查找历史作文
 * - [ ] 支持作文标签 (Tags) 系统
 * - [ ] 实现草稿箱功能，支持未完成作文的保存
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { Database } from '../database/db';

export interface Essay {
  id: number;
  user_id: number;
  title: string;
  content: string;
  correction: string;
  score_json: any;
  created_at: number;
  updated_at: number;
}

export class EssayModel {
  constructor(private db: Database) {}

  /**
   * 创建作文记录
   */
  async create(userId: number, content: string, correction: string, scoreJson: any, title?: string): Promise<number> {
    const now = Date.now();
    return await this.db.insert(
      `INSERT INTO essays (user_id, title, content, correction, score_json, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [userId, title || 'Untitled', content, correction, JSON.stringify(scoreJson), now, now]
    );
  }

  /**
   * 获取用户的作文历史
   */
  async getHistory(userId: number, limit: number = 10, offset: number = 0): Promise<Essay[]> {
    const rows = await this.db.all(
      'SELECT * FROM essays WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?',
      [userId, limit, offset]
    );
    return rows.map(row => ({
        ...row,
        score_json: row.score_json ? JSON.parse(row.score_json) : null
    }));
  }

  /**
   * 根据 ID 获取作文
   */
  async getById(id: number): Promise<Essay | null> {
    const row = await this.db.get('SELECT * FROM essays WHERE id = ?', [id]);
    if (!row) return null;
    return {
        ...row,
        score_json: row.score_json ? JSON.parse(row.score_json) : null
    };
  }
}
