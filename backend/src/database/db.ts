/**
 * @fileoverview 数据库连接管理模块 (Database Connection Manager)
 * @description
 * 该文件封装了 SQLite 数据库的核心操作，负责数据库的生命周期管理、表结构初始化和基础 CRUD 接口。
 * 
 * 主要功能：
 * 1. 连接管理：自动初始化数据库文件，处理连接和关闭
 * 2. 自动迁移 (Auto-migration)：
 *    - 在启动时检查并创建所有必要的表结构 (Users, Sessions, LearningRecords, Vocabulary, Essays 等)
 *    - 确保数据库 Schema 与代码版本保持一致
 * 3. Promise 封装：将 sqlite3 的回调风格 API 封装为现代的 Promise/Async 风格
 *    - run: 执行无返回值的 SQL (UPDATE, DELETE)
 *    - get: 查询单行数据
 *    - all: 查询多行数据
 *    - insert: 执行插入并返回 lastID
 * 4. 性能优化：自动创建必要的索引
 * 
 * 数据表概览：
 * - users: 用户账户
 * - sessions: 登录会话
 * - learning_records: 通用学习日志
 * - vocabulary: 生词本 (SRS)
 * - essays: 作文及批改
 * - students: 学生档案
 * - language_profiles: 能力维度评分
 * - learning_paths: 学习路径
 * 
 * 待改进项：
 * - [ ] 引入 ORM (如 Prisma 或 TypeORM) 以简化查询构建
 * - [ ] 实现数据库连接池 (虽然 SQLite 是单文件，但可优化并发读)
 * - [ ] 增加数据库备份和恢复机制
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import sqlite3 from 'sqlite3';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import { createLogger } from '../utils/logger';
import { config } from '../config/env';

const logger = createLogger('Database');

export class Database {
  private db: sqlite3.Database | null = null;

  /**
   * 初始化数据库连接
   * 如果数据库文件不存在，会自动创建。
   * 连接成功后会自动运行迁移脚本以确保表结构最新。
   */
  async initialize(): Promise<void> {
    const dbPath = path.resolve(__dirname, config.database.path);
    const dbDir = path.dirname(dbPath);

    // 确保数据库目录存在
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true });
    }

    logger.info({ dbPath }, 'Initializing database...');

    return new Promise((resolve, reject) => {
      this.db = new sqlite3.Database(dbPath, (err) => {
        if (err) {
          logger.error({ error: err.message }, 'Failed to connect to database');
          reject(err);
        } else {
          logger.info('Database connected');
          this.runMigrations()
            .then(() => resolve())
            .catch(reject);
        }
      });
    });
  }

  /**
   * 运行数据库迁移
   * 创建或更新所有必要的数据库表结构。
   * 包含：用户、会话、学习记录、语言档案、微调数据、学生档案、生词本、作文、学习路径等表。
   */
  private async runMigrations(): Promise<void> {
    logger.info('Running database migrations...');

    // 启用外键约束 (SQLite 默认关闭)
    await this.run('PRAGMA foreign_keys = ON');

    // 创建用户表 (Users)
    // 存储用户的基本认证信息
    await this.run(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
      )
    `);

    // 创建会话表 (Sessions)
    // 存储用户的登录会话信息，支持多设备登录管理
    await this.run(`
      CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        user_id INTEGER,
        peer_id TEXT NOT NULL, -- 客户端设备标识
        capabilities TEXT NOT NULL, -- 客户端能力描述 (JSON)
        created_at INTEGER NOT NULL,
        last_heartbeat INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // 创建学习记录表 (Learning Records)
    // 存储用户的所有学习活动日志，用于分析和回顾
    await this.run(`
      CREATE TABLE IF NOT EXISTS learning_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL, -- 记录类型: vocabulary, essay, dialogue, analysis
        content TEXT NOT NULL, -- 记录内容 (如查询的单词、作文原文)
        metadata TEXT, -- 扩展元数据 (JSON)，如评分、分析结果、Token消耗
        created_at INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // 创建语言档案表 (Language Profiles)
    // 存储用户的语言能力多维度评分
    await this.run(`
      CREATE TABLE IF NOT EXISTS language_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        dimension TEXT NOT NULL, -- 维度: vocabulary, grammar, fluency, etc.
        score REAL NOT NULL, -- 分数 (0-100)
        analysis TEXT, -- 详细分析文本
        updated_at INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // 创建 LLM 微调数据表 (LLM Finetune Data)
    // 收集高质量的用户交互数据，用于后续模型微调
    await this.run(`
      CREATE TABLE IF NOT EXISTS llm_finetune_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        prompt TEXT NOT NULL, -- 输入提示词
        response TEXT NOT NULL, -- 模型输出
        feedback TEXT, -- 用户反馈或修正
        created_at INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // 创建学生档案表 (Students)
    // 存储学生的个性化设置和学习目标
    await this.run(`
      CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        level TEXT DEFAULT 'beginner', -- 当前水平
        goals TEXT, -- 学习目标 (JSON)
        interests TEXT, -- 兴趣爱好 (JSON)
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // 创建词汇表 (Vocabulary / 生词本)
    // 存储用户收藏的生词及其掌握程度
    await this.run(`
      CREATE TABLE IF NOT EXISTS vocabulary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        word TEXT NOT NULL,
        definition TEXT,
        pronunciation TEXT,
        example TEXT,
        mastery_level INTEGER DEFAULT 0, -- 掌握程度 (0-5)
        next_review_at INTEGER, -- 下次复习时间 (间隔重复算法)
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // 创建作文表 (Essays)
    // 专门存储作文及其批改记录
    await this.run(`
      CREATE TABLE IF NOT EXISTS essays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT,
        content TEXT NOT NULL, -- 作文原文
        correction TEXT, -- 批改后的文本
        score_json TEXT, -- 评分详情 (JSON)
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // 创建学习路径表 (Learning Paths)
    // 存储系统生成的个性化学习路径
    await this.run(`
      CREATE TABLE IF NOT EXISTS learning_paths (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        milestones TEXT, -- 里程碑列表 (JSON array)
        status TEXT DEFAULT 'active', -- 状态: active, completed, archived
        progress INTEGER DEFAULT 0, -- 进度百分比 (0-100)
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // 创建索引以优化查询性能
    await this.run('CREATE INDEX IF NOT EXISTS idx_learning_records_user_id ON learning_records(user_id)');
    await this.run('CREATE INDEX IF NOT EXISTS idx_learning_records_type ON learning_records(type)');
    await this.run('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)');
    await this.run('CREATE INDEX IF NOT EXISTS idx_language_profiles_user_id ON language_profiles(user_id)');
    await this.run('CREATE INDEX IF NOT EXISTS idx_vocabulary_user_id ON vocabulary(user_id)');
    await this.run('CREATE INDEX IF NOT EXISTS idx_essays_user_id ON essays(user_id)');
    await this.run('CREATE INDEX IF NOT EXISTS idx_learning_paths_user_id ON learning_paths(user_id)');

    logger.info('Database migrations completed');
  }

  /**
   * 执行 SQL 语句（无返回值）
   * 适用于 UPDATE, DELETE, CREATE 等操作
   * @param sql SQL 语句
   * @param params 参数数组
   */
  run(sql: string, params: any[] = []): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        return reject(new Error('Database not initialized'));
      }

      this.db.run(sql, params, (err) => {
        if (err) {
          logger.error({ sql, params, error: err.message }, 'SQL run failed');
          reject(err);
        } else {
          resolve();
        }
      });
    });
  }

  /**
   * 查询单行数据
   * 适用于 SELECT ... LIMIT 1
   * @param sql SQL 语句
   * @param params 参数数组
   */
  get<T = any>(sql: string, params: any[] = []): Promise<T | undefined> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        return reject(new Error('Database not initialized'));
      }

      this.db.get(sql, params, (err, row) => {
        if (err) {
          logger.error({ sql, params, error: err.message }, 'SQL get failed');
          reject(err);
        } else {
          resolve(row as T | undefined);
        }
      });
    });
  }

  /**
   * 查询多行数据
   * 适用于 SELECT ...
   * @param sql SQL 语句
   * @param params 参数数组
   */
  all<T = any>(sql: string, params: any[] = []): Promise<T[]> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        return reject(new Error('Database not initialized'));
      }

      this.db.all(sql, params, (err, rows) => {
        if (err) {
          logger.error({ sql, params, error: err.message }, 'SQL all failed');
          reject(err);
        } else {
          resolve(rows as T[]);
        }
      });
    });
  }

  /**
   * 执行插入操作并返回新插入行的 ID
   * 适用于 INSERT INTO ...
   * @param sql SQL 语句
   * @param params 参数数组
   */
  insert(sql: string, params: any[] = []): Promise<number> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        return reject(new Error('Database not initialized'));
      }

      this.db.run(sql, params, function (err) {
        if (err) {
          logger.error({ sql, params, error: err.message }, 'SQL insert failed');
          reject(err);
        } else {
          resolve(this.lastID);
        }
      });
    });
  }

  /**
   * 关闭数据库连接
   */
  async close(): Promise<void> {
    if (!this.db) {
      return;
    }

    return new Promise((resolve, reject) => {
      this.db!.close((err) => {
        if (err) {
          logger.error({ error: err.message }, 'Failed to close database');
          reject(err);
        } else {
          logger.info('Database connection closed');
          this.db = null;
          resolve();
        }
      });
    });
  }
}
