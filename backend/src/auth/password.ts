/**
 * @fileoverview 密码管理模块 (Password Management)
 * @description
 * 该文件封装了密码安全相关的核心功能，包括哈希加密、验证和强度检查。
 * 
 * 主要功能：
 * 1. 密码哈希：使用 bcrypt 算法对用户密码进行单向加密存储
 * 2. 密码验证：比对明文密码与数据库中存储的哈希值
 * 3. 强度检查：强制执行密码复杂度策略（长度、大小写、数字）
 * 
 * 安全性：
 * - 使用 bcryptjs 库，自动处理加盐 (Salt)
 * - 默认 Salt Rounds 为 10，平衡安全性与性能
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import bcrypt from 'bcryptjs';
import { createLogger } from '../utils/logger';

const logger = createLogger('Password');

const SALT_ROUNDS = 10;

/**
 * 哈希密码
 * 使用 bcrypt 对明文密码进行加密
 * 
 * @param password 明文密码
 * @returns 加密后的哈希字符串
 */
export async function hashPassword(password: string): Promise<string> {
  try {
    const hash = await bcrypt.hash(password, SALT_ROUNDS);
    return hash;
  } catch (error: any) {
    logger.error({ error: error.message }, 'Password hashing failed');
    throw new Error('Failed to hash password');
  }
}

/**
 * 验证密码
 * 比较明文密码与存储的哈希值是否匹配
 * 
 * @param password 明文密码
 * @param hash 存储的哈希值
 * @returns 匹配返回 true，否则返回 false
 */
export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  try {
    const isValid = await bcrypt.compare(password, hash);
    return isValid;
  } catch (error: any) {
    logger.error({ error: error.message }, 'Password verification failed');
    return false;
  }
}

/**
 * 验证密码强度
 * 规则：至少 8 个字符，包含大小写字母和数字
 * 
 * @param password 待检查的密码
 * @returns 包含验证结果和错误信息的对象
 */
export function validatePasswordStrength(password: string): { valid: boolean; message?: string } {
  if (password.length < 8) {
    return { valid: false, message: 'Password must be at least 8 characters long' };
  }

  if (!/[a-z]/.test(password)) {
    return { valid: false, message: 'Password must contain at least one lowercase letter' };
  }

  if (!/[A-Z]/.test(password)) {
    return { valid: false, message: 'Password must contain at least one uppercase letter' };
  }

  if (!/[0-9]/.test(password)) {
    return { valid: false, message: 'Password must contain at least one number' };
  }

  return { valid: true };
}
