/**
 * @fileoverview 词汇数据模型 (Vocabulary Model)
 * 
 * 管理用户的生词本和复习进度。
 * 实现了基于间隔重复 (Spaced Repetition) 算法的词汇记忆管理。
 * 
 * 主要功能：
 * 1. 生词管理 (Add/Update)：添加新词或更新现有词汇信息
 * 2. 复习队列 (GetDue)：获取当前需要复习的单词列表
 * 3. 进度更新 (UpdateMastery)：根据复习结果调整掌握程度和下次复习时间
 * 4. 间隔重复算法：实现了简化的 SM-2 类似算法，动态调整复习间隔
 * 
 * 待改进项：
 * - [ ] 升级为更先进的 FSRS (Free Spaced Repetition Scheduler) 算法
 * - [ ] 支持短语和例句的专项复习模式
 * - [ ] 增加单词发音音频的存储或即时生成缓存
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { Database } from '../database/db';

export interface VocabularyItem {
  id: number;
  user_id: number;
  word: string;
  definition: string;
  pronunciation: string;
  example: string;
  mastery_level: number;
  next_review_at: number;
  created_at: number;
  updated_at: number;
}

export class VocabularyModel {
  constructor(private db: Database) {}

  /**
   * 添加或更新生词
   */
  async addWord(userId: number, word: string, data: { definition?: string; pronunciation?: string; example?: string }): Promise<number> {
    const now = Date.now();
    // 默认下次复习时间为现在 (立即复习)
    const nextReview = now; 

    // 检查是否已存在
    const existing = await this.db.get('SELECT id FROM vocabulary WHERE user_id = ? AND word = ?', [userId, word]);
    if (existing) {
        // 更新现有记录
        await this.db.run(
            'UPDATE vocabulary SET definition = ?, pronunciation = ?, example = ?, updated_at = ? WHERE id = ?',
            [data.definition || '', data.pronunciation || '', data.example || '', now, existing.id]
        );
        return existing.id;
    }

    return await this.db.insert(
      `INSERT INTO vocabulary (user_id, word, definition, pronunciation, example, mastery_level, next_review_at, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)`,
      [userId, word, data.definition || '', data.pronunciation || '', data.example || '', nextReview, now, now]
    );
  }

  /**
   * 获取待复习的单词
   */
  async getDueWords(userId: number, limit: number = 20): Promise<VocabularyItem[]> {
    const now = Date.now();
    return await this.db.all(
      'SELECT * FROM vocabulary WHERE user_id = ? AND next_review_at <= ? ORDER BY next_review_at ASC LIMIT ?',
      [userId, now, limit]
    );
  }

  /**
   * 更新单词掌握程度 (复习打卡)
   * 使用简化的间隔重复算法 (类似 SM-2)
   */
  async updateMastery(id: number, correct: boolean): Promise<void> {
    const item = await this.db.get('SELECT * FROM vocabulary WHERE id = ?', [id]);
    if (!item) return;

    let newLevel = item.mastery_level;
    let nextReview = Date.now();

    if (correct) {
        newLevel += 1;
        // 间隔: 1天, 3天, 7天, 14天, 30天...
        const days = Math.pow(2, newLevel - 1); 
        nextReview += days * 24 * 60 * 60 * 1000;
    } else {
        newLevel = Math.max(0, newLevel - 1);
        // 答错后 10 分钟再次复习
        nextReview += 10 * 60 * 1000; 
    }

    await this.db.run(
        'UPDATE vocabulary SET mastery_level = ?, next_review_at = ?, updated_at = ? WHERE id = ?',
        [newLevel, nextReview, Date.now(), id]
    );
  }
}
