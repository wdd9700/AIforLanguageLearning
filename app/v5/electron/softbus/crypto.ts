/**
 * @fileoverview 软总线加密与安全模块 (Softbus Crypto & Security)
 * @description
 * 该模块提供了软总线所需的加密、签名和身份认证功能。
 * 
 * 主要功能包括：
 * 1. 密钥管理 (Key Management)：
 *    - 生成 Ed25519 密钥对 (generateKeyPair)
 *    - 派生 PeerID (derivePeerId)
 *    - 派生 PSK (derivePsk)
 * 
 * 2. 签名与验证 (Signing & Verification)：
 *    - 数字签名 (sign)
 *    - 签名验证 (verify)
 * 
 * 3. 加密与解密 (Encryption & Decryption)：
 *    - AES-256-GCM 对称加密 (encrypt, decrypt)
 * 
 * 4. 身份认证 (Authentication)：
 *    - 握手消息生成与验证 (createHandshakeMessage, verifyHandshakeMessage)
 *    - 证书颁发与验证 (issueCertificate, verifyCertificate)
 *    - 白名单管理 (Whitelist)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import * as crypto from 'crypto';

/**
 * 生成 Ed25519 密钥对
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
 * PeerID 派生：基于公钥的 SHA256 哈希
 */
export function derivePeerId(publicKey: string): string {
  const hash = crypto.createHash('sha256').update(publicKey).digest('hex');
  return hash.substring(0, 16); // 取前 16 字符作为 PeerID
}

/**
 * 数字签名（使用 Ed25519）
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
 * 对称加密（使用 AES-256-GCM）
 * PSK: 预共享密钥
 */
export interface EncryptedData {
  ciphertext: Uint8Array;
  iv: Uint8Array;
  authTag: Uint8Array;
}

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
 * PSK 派生（基于密码短语 HKDF）
 */
export function derivePsk(passphrase: string, salt: string = 'mmls-softbus'): string {
  const hkdf = crypto.hkdfSync('sha256', passphrase, salt, 'psk-key', 32);
  return (hkdf as any).toString('hex');
}

/**
 * 生成临时会话密钥（用于握手后的通信）
 */
export function generateSessionKey(): string {
  return crypto.randomBytes(32).toString('hex');
}

/**
 * 握手消息格式（Curve25519 风格）
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
 * 证书结构（简化版）
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
 * 验证证书
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
 * 白名单管理
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
