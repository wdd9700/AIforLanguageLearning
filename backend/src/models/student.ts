/**
 * @fileoverview 学生档案数据模型 (Student Profile Model)
 * @description
 * 该文件定义了学生档案 (Student Profile) 的数据结构和数据库操作方法。
 * 
 * 主要功能：
 * 1. 数据结构：定义 StudentProfile 接口，包含当前水平 (Level)、学习目标 (Goals) 和兴趣爱好 (Interests)
 * 2. 档案查询：获取特定用户的详细学习档案
 * 3. 档案更新：支持创建新档案或更新现有档案的部分字段 (Upsert 逻辑)
 * 
 * 数据库表：students
 * 
 * 待改进项：
 * - [ ] 支持多目标语言的学习档案管理
 * - [ ] 细化技能维度 (听说读写) 的独立进度追踪
 * - [ ] 增加学习偏好设置 (如每日学习时长、提醒时间)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { Database } from '../database/db';
import { createLogger } from '../utils/logger';

const logger = createLogger('StudentModel');

export interface StudentProfile {
  id: number;
  user_id: number;
  level: string;
  goals: string[];
  interests: string[];
  created_at: number;
  updated_at: number;
}

export class StudentModel {
  constructor(private db: Database) {}

  /**
   * 获取学生档案
   */
  async getProfile(userId: number): Promise<StudentProfile | null> {
    const row = await this.db.get('SELECT * FROM students WHERE user_id = ?', [userId]);
    if (!row) return null;
    
    return {
      ...row,
      goals: row.goals ? JSON.parse(row.goals) : [],
      interests: row.interests ? JSON.parse(row.interests) : []
    };
  }

  /**
   * 更新或创建学生档案
   */
  async updateProfile(userId: number, data: { level?: string; goals?: string[]; interests?: string[] }): Promise<void> {
    const existing = await this.getProfile(userId);
    const now = Date.now();

    if (existing) {
      const updates: string[] = [];
      const params: any[] = [];

      if (data.level !== undefined) {
        updates.push('level = ?');
        params.push(data.level);
      }
      if (data.goals !== undefined) {
        updates.push('goals = ?');
        params.push(JSON.stringify(data.goals));
      }
      if (data.interests !== undefined) {
        updates.push('interests = ?');
        params.push(JSON.stringify(data.interests));
      }

      if (updates.length > 0) {
        updates.push('updated_at = ?');
        params.push(now);
        params.push(userId);
        await this.db.run(`UPDATE students SET ${updates.join(', ')} WHERE user_id = ?`, params);
      }
    } else {
      await this.db.run(
        `INSERT INTO students (user_id, level, goals, interests, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)`,
        [
          userId,
          data.level || 'beginner',
          JSON.stringify(data.goals || []),
          JSON.stringify(data.interests || []),
          now,
          now
        ]
      );
    }
  }
}
