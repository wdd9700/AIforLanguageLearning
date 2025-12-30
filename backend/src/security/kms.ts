/**
 * @fileoverview 密钥管理服务 (KMS)
 * 
 * 负责管理系统的主密钥 (Master Key) 和敏感数据的加解密操作。
 * 使用 AES-256-GCM 算法确保数据的机密性和完整性。
 * 
 * 主要功能：
 * 1. 密钥管理：自动加载或生成主密钥，并安全存储 (0600 权限)
 * 2. 数据加密 (Encrypt)：使用主密钥加密数据，生成包含 IV 和 AuthTag 的密文
 * 3. 数据解密 (Decrypt)：验证 AuthTag 并解密数据
 * 4. 密钥轮换 (Rotate)：预留接口用于未来实现密钥更新
 * 
 * 待改进项：
 * - [ ] 实现密钥轮换 (Key Rotation) 逻辑：解密旧数据 -> 生成新密钥 -> 重新加密
 * - [ ] 支持密钥备份与恢复机制
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';
import { config } from '../config/env';

const ALGORITHM = 'aes-256-gcm';
const KMK_PATH = path.join(__dirname, '../../data/kmk.key');

/**
 * 密钥管理服务 (KMS)
 * 负责管理主密钥 (Master Key) 和数据的加解密
 * 使用 AES-256-GCM 算法保证数据的机密性和完整性
 */
export class KMS {
  private static instance: KMS;
  private masterKey: Buffer;

  private constructor() {
    this.masterKey = this.loadOrGenerateMasterKey();
  }

  public static getInstance(): KMS {
    if (!KMS.instance) {
      KMS.instance = new KMS();
    }
    return KMS.instance;
  }

  /**
   * 加载或生成密钥管理密钥 (主密钥)
   * 如果密钥文件存在则加载，否则生成新密钥并保存
   */
  private loadOrGenerateMasterKey(): Buffer {
    try {
      if (fs.existsSync(KMK_PATH)) {
        const keyHex = fs.readFileSync(KMK_PATH, 'utf-8');
        return Buffer.from(keyHex, 'hex');
      }
    } catch (error) {
      console.error('加载 KMK 失败，正在生成新密钥:', error);
    }

    // 生成新的 256 位密钥
    const newKey = crypto.randomBytes(32);
    this.saveMasterKey(newKey);
    return newKey;
  }

  /**
   * 保存主密钥到文件系统
   * 设置严格的文件权限 (0600) 以保护密钥安全
   */
  private saveMasterKey(key: Buffer): void {
    try {
      const dir = path.dirname(KMK_PATH);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      fs.writeFileSync(KMK_PATH, key.toString('hex'), { mode: 0o600 }); // 仅所有者可读写
    } catch (error) {
      console.error('保存 KMK 失败:', error);
    }
  }

  /**
   * 使用主密钥加密数据
   * @param text 待加密的明文
   * @returns 格式化的加密字符串 (IV:AuthTag:EncryptedData)
   */
  public encrypt(text: string): string {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv(ALGORITHM, this.masterKey, iv);
    
    let encrypted = cipher.update(text, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    const authTag = cipher.getAuthTag();

    // 格式: IV:AuthTag:EncryptedData
    return `${iv.toString('hex')}:${authTag.toString('hex')}:${encrypted}`;
  }

  /**
   * 使用主密钥解密数据
   * @param encryptedText 加密字符串
   * @returns 解密后的明文
   */
  public decrypt(encryptedText: string): string {
    const parts = encryptedText.split(':');
    if (parts.length !== 3) {
      throw new Error('无效的加密格式');
    }

    const iv = Buffer.from(parts[0], 'hex');
    const authTag = Buffer.from(parts[1], 'hex');
    const encrypted = parts[2];

    const decipher = crypto.createDecipheriv(ALGORITHM, this.masterKey, iv);
    decipher.setAuthTag(authTag);

    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');

    return decrypted;
  }

  /**
   * 轮换主密钥
   * (重新加密所有数据 - 预留给未来实现)
   */
  public rotateKey(): void {
    // 1. 生成新密钥
    // 2. 使用旧密钥解密所有敏感数据
    // 3. 使用新密钥加密
    // 4. 保存新密钥
    throw new Error('密钥轮换功能尚未实现');
  }
}
