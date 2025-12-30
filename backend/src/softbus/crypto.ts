/**
 * @fileoverview 软总线加密模块 (Softbus Crypto)
 * 
 * 基于 ZeroMQ 安全架构 (CurveZMQ) 的加密与身份验证实现。
 * 提供密钥生成、签名验证、对称加密和证书管理功能，确保软总线通信的安全性。
 * 
 * 主要功能：
 * 1. 密钥管理：生成 Ed25519 密钥对，派生 PeerID 和 PSK
 * 2. 数字签名：基于 Ed25519 的消息签名与验证
 * 3. 数据加密：使用 AES-256-GCM 进行对称加密和解密
 * 4. 握手协议：创建和验证握手消息，确保节点身份合法
 * 5. 证书管理：颁发和验证自签名证书
 * 6. 访问控制：简单的白名单管理机制
 * 
 * 待改进项：
 * 1. 实现密钥轮换 (Key Rotation) 机制，提高长期通信的安全性
 * 2. 支持更多加密算法 (如 ChaCha20-Poly1305) 以适应不同性能需求的设备
 * 3. 增强私钥存储的安全性，支持硬件安全模块 (HSM) 或系统密钥库
 * 4. 完善证书吊销列表 (CRL) 机制
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import * as crypto from 'crypto';

/**
 * 生成 Ed25519 密钥对
 * 用于数字签名和身份验证
 */
export function generateKeyPair(): { publicKey: string; privateKey: string } {
  const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519', {
    publicKeyEncoding: {
      format: 'spki',
      type: 'spki',
    },
    privateKeyEncoding: {
      format: 'pkcs8',
      type: 'pkcs8',
    },
  });

  return {
    publicKey: (publicKey as any).toString('base64'),
    privateKey: (privateKey as any).toString('base64'),
  };
}

/**
 * PeerID 派生
 * 基于公钥的 SHA256 哈希生成唯一的节点标识符
 * @param publicKey Base64 编码的公钥
 * @returns 16 字符长度的 PeerID
 */
export function derivePeerId(publicKey: string): string {
  const hash = crypto.createHash('sha256').update(publicKey).digest('hex');
  return hash.substring(0, 16); // 取前 16 字符作为 PeerID
}

/**
 * 数字签名 (Ed25519)
 * @param message 待签名的消息数据
 * @param privateKeyPem PEM 格式的私钥
 * @returns 签名数据
 */
export function sign(message: Uint8Array, privateKeyPem: string): Uint8Array {
  const signer = crypto.createSign('SHA256');
  signer.update(message);
  // 将 PEM 格式私钥转换为 Node 可用格式
  const signature = signer.sign(privateKeyPem, 'binary');
  return new Uint8Array(Buffer.from(signature, 'binary'));
}

/**
 * 验证签名
 * @param message 原始消息数据
 * @param signature 签名数据
 * @param publicKeyPem PEM 格式的公钥
 * @returns 验证结果
 */
export function verify(message: Uint8Array, signature: Uint8Array, publicKeyPem: string): boolean {
  try {
    const verifier = crypto.createVerify('SHA256');
    verifier.update(message);
    return verifier.verify(publicKeyPem, Buffer.from(signature));
  } catch {
    return false;
  }
}

/**
 * 对称加密数据结构
 */
export interface EncryptedData {
  ciphertext: Uint8Array; // 密文
  iv: Uint8Array;         // 初始化向量
  authTag: Uint8Array;    // 认证标签 (GCM)
}

/**
 * 对称加密 (AES-256-GCM)
 * @param plaintext 明文数据
 * @param psk 预共享密钥 (Pre-Shared Key)
 * @returns 加密后的数据对象
 */
export function encrypt(plaintext: Uint8Array, psk: string): EncryptedData {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', Buffer.from(psk, 'hex'), iv);

  const encrypted = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const authTag = cipher.getAuthTag();

  return {
    ciphertext: new Uint8Array(encrypted),
    iv: new Uint8Array(iv),
    authTag: new Uint8Array(authTag),
  };
}

/**
 * 对称解密
 * @param data 加密数据对象
 * @param psk 预共享密钥
 * @returns 解密后的明文，失败返回 null
 */
export function decrypt(data: EncryptedData, psk: string): Uint8Array | null {
  try {
    const decipher = crypto.createDecipheriv('aes-256-gcm', Buffer.from(psk, 'hex'), data.iv);
    decipher.setAuthTag(data.authTag);

    const decrypted = Buffer.concat([
      decipher.update(data.ciphertext),
      decipher.final(),
    ]);

    return new Uint8Array(decrypted);
  } catch {
    return null;
  }
}

/**
 * PSK 派生
 * 使用 HKDF 基于密码短语生成强密钥
 * @param passphrase 密码短语
 * @param salt 盐值
 * @returns 派生的密钥 (Hex 字符串)
 */
export function derivePsk(passphrase: string, salt: string = 'mmls-softbus'): string {
  const hkdf = crypto.hkdfSync('sha256', passphrase, salt, 'psk-key', 32);
  return Buffer.from(hkdf).toString('hex');
}

/**
 * 生成临时会话密钥
 * 用于握手后的加密通信
 */
export function generateSessionKey(): string {
  return crypto.randomBytes(32).toString('hex');
}

/**
 * 握手消息格式 (Curve25519 风格)
 */
export interface HandshakeMessage {
  version: number;
  peerId: string;
  publicKey: string;
  signature: string; // 对 peerId 的签名
  timestamp: number;
}

/**
 * 创建握手消息
 * @param peerId 节点 ID
 * @param publicKey 公钥
 * @param privateKeyPem 私钥
 * @returns 握手消息对象
 */
export function createHandshakeMessage(
  peerId: string,
  publicKey: string,
  privateKeyPem: string
): HandshakeMessage {
  const payload = new TextEncoder().encode(`${peerId}-${publicKey}-${Date.now()}`);
  const signature = sign(payload, privateKeyPem);

  return {
    version: 1,
    peerId,
    publicKey,
    signature: Buffer.from(signature).toString('base64'),
    timestamp: Date.now(),
  };
}

/**
 * 验证握手消息
 */
export function verifyHandshakeMessage(msg: HandshakeMessage, publicKeyPem: string): boolean {
  try {
    const payload = new TextEncoder().encode(`${msg.peerId}-${msg.publicKey}-${msg.timestamp}`);
    const signature = new Uint8Array(Buffer.from(msg.signature, 'base64'));
    return verify(payload, signature, publicKeyPem);
  } catch {
    return false;
  }
}

/**
 * 证书结构 (简化版)
 */
export interface Certificate {
  issuer: string;
  subject: string;
  publicKey: string;
  signature: string;
  validFrom: number;
  validTo: number;
}

/**
 * 颁发自签名证书
 * @param subject 证书主体
 * @param publicKey 公钥
 * @param privateKeyPem 私钥
 * @param validDays 有效期天数
 * @returns 证书对象
 */
export function issueCertificate(
  subject: string,
  publicKey: string,
  privateKeyPem: string,
  validDays: number = 365
): Certificate {
  const now = Date.now();
  const cert: Certificate = {
    issuer: subject, // 自签
    subject,
    publicKey,
    signature: '',
    validFrom: now,
    validTo: now + validDays * 24 * 60 * 60 * 1000,
  };

  // 对证书内容签名
  const certPayload = new TextEncoder().encode(
    `${cert.issuer}-${cert.subject}-${cert.publicKey}-${cert.validFrom}-${cert.validTo}`
  );
  const signature = sign(certPayload, privateKeyPem);
  cert.signature = Buffer.from(signature).toString('base64');

  return cert;
}

/**
 * 验证证书有效性
 */
export function verifyCertificate(cert: Certificate, publicKeyPem: string): boolean {
  const now = Date.now();
  if (now < cert.validFrom || now > cert.validTo) {
    return false; // 证书过期
  }

  const certPayload = new TextEncoder().encode(
    `${cert.issuer}-${cert.subject}-${cert.publicKey}-${cert.validFrom}-${cert.validTo}`
  );
  const signature = new Uint8Array(Buffer.from(cert.signature, 'base64'));
  return verify(certPayload, signature, publicKeyPem);
}

/**
 * 白名单管理类
 * 用于控制允许连接的节点
 */
export class Whitelist {
  private allowedPeers: Set<string> = new Set();

  add(peerId: string): void {
    this.allowedPeers.add(peerId);
  }

  remove(peerId: string): void {
    this.allowedPeers.delete(peerId);
  }

  contains(peerId: string): boolean {
    return this.allowedPeers.has(peerId);
  }

  clear(): void {
    this.allowedPeers.clear();
  }

  list(): string[] {
    return Array.from(this.allowedPeers);
  }
}
