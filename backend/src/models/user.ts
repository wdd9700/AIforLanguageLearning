/**
 * @fileoverview 用户数据模型 (User Model)
 * 
 * 负责用户账户的创建、查询、验证和管理。
 * 封装了对 users 表的数据库操作，包括密码哈希处理和凭据验证。
 * 
 * 主要功能：
 * 1. 用户创建 (Create)：包含唯一性检查和密码加密
 * 2. 用户查询 (Read)：支持按 ID、用户名、邮箱查询
 * 3. 凭据验证 (Verify)：验证用户名和密码是否匹配
 * 4. 密码更新 (Update)：更新用户密码
 * 5. 用户删除 (Delete)：删除用户账户
 * 
 * 待改进项：
 * - [ ] 增加软删除 (Soft Delete) 支持，保留数据恢复能力
 * - [ ] 引入用户角色 (Roles) 和权限 (Permissions) 字段
 * - [ ] 记录最后登录时间和 IP 地址
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { Database } from '../database/db';
import { hashPassword, verifyPassword } from '../auth/password';
import { createLogger } from '../utils/logger';

const logger = createLogger('UserModel');

/**
 * 用户接口
 * 对应数据库中的 users 表结构
 */
export interface User {
  id: number;
  username: string;
  email: string;
  password_hash: string;
  created_at: number;
  updated_at: number;
}

/**
 * 用户创建参数接口
 */
export interface CreateUserParams {
  username: string;
  email: string;
  password: string;
}

/**
 * 用户模型类
 * 提供对用户表的 CRUD 操作及认证辅助方法
 */
export class UserModel {
  constructor(private db: Database) {}

  /**
   * 创建新用户
   * 包含用户名/邮箱唯一性检查和密码哈希处理
   * 
   * @param params 创建参数
   * @returns 创建成功的用户对象
   * @throws Error 如果用户名或邮箱已存在
   */
  async create(params: CreateUserParams): Promise<User> {
    const { username, email, password } = params;

    // 检查用户名是否已存在
    const existingUser = await this.findByUsername(username);
    if (existingUser) {
      throw new Error('Username already exists');
    }

    // 检查邮箱是否已存在
    const existingEmail = await this.findByEmail(email);
    if (existingEmail) {
      throw new Error('Email already exists');
    }

    // 哈希密码
    const passwordHash = await hashPassword(password);

    // 插入用户
    const now = Date.now();
    const userId = await this.db.insert(
      `INSERT INTO users (username, email, password_hash, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?)`,
      [username, email, passwordHash, now, now]
    );

    logger.info({ userId, username }, 'User created');

    return {
      id: userId,
      username,
      email,
      password_hash: passwordHash,
      created_at: now,
      updated_at: now,
    };
  }

  /**
   * 通过用户名查找用户
   * 
   * @param username 用户名
   * @returns 用户对象或 undefined
   */
  async findByUsername(username: string): Promise<User | undefined> {
    return this.db.get<User>('SELECT * FROM users WHERE username = ?', [username]);
  }

  /**
   * 通过邮箱查找用户
   * 
   * @param email 邮箱地址
   * @returns 用户对象或 undefined
   */
  async findByEmail(email: string): Promise<User | undefined> {
    return this.db.get<User>('SELECT * FROM users WHERE email = ?', [email]);
  }

  /**
   * 通过 ID 查找用户
   * 
   * @param id 用户ID
   * @returns 用户对象或 undefined
   */
  async findById(id: number): Promise<User | undefined> {
    return this.db.get<User>('SELECT * FROM users WHERE id = ?', [id]);
  }

  /**
   * 获取所有用户 (分页)
   * 
   * @param limit 每页数量，默认 50
   * @param offset 偏移量，默认 0
   * @returns 包含用户列表和总数的对象
   */
  async findAll(limit: number = 50, offset: number = 0): Promise<{ users: User[], total: number }> {
    const users = await this.db.all<User>('SELECT id, username, email, created_at, updated_at FROM users LIMIT ? OFFSET ?', [limit, offset]);
    const countResult = await this.db.get<{ count: number }>('SELECT COUNT(*) as count FROM users');
    return {
        users,
        total: countResult?.count || 0
    };
  }

  /**
   * 验证用户凭据
   * 检查用户名是否存在且密码匹配
   * 
   * @param username 用户名
   * @param password 明文密码
   * @returns 验证通过返回用户对象，否则返回 null
   */
  async verifyCredentials(username: string, password: string): Promise<User | null> {
    const user = await this.findByUsername(username);
    if (!user) {
      return null;
    }

    const isValid = await verifyPassword(password, user.password_hash);
    if (!isValid) {
      return null;
    }

    return user;
  }

  /**
   * 更新用户密码
   * 
   * @param userId 用户ID
   * @param newPassword 新密码（明文）
   */
  async updatePassword(userId: number, newPassword: string): Promise<void> {
    const passwordHash = await hashPassword(newPassword);
    const now = Date.now();

    await this.db.run(
      'UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?',
      [passwordHash, now, userId]
    );

    logger.info({ userId }, 'User password updated');
  }

  /**
   * 删除用户
   * 
   * @param userId 用户ID
   */
  async delete(userId: number): Promise<void> {
    await this.db.run('DELETE FROM users WHERE id = ?', [userId]);
    logger.info({ userId }, 'User deleted');
  }
}
