/**
 * Softbus - ZeroMQ-based P2P Message Bus
 * Encryption & Identity (CurveZMQ-inspired)
 */
/**
 * 生成 Ed25519 密钥对
 */
export declare function generateKeyPair(): {
    publicKey: string;
    privateKey: string;
};
/**
 * PeerID 派生：基于公钥的 SHA256 哈希
 */
export declare function derivePeerId(publicKey: string): string;
/**
 * 数字签名（使用 Ed25519）
 */
export declare function sign(message: Uint8Array, privateKeyPem: string): Uint8Array;
/**
 * 验证签名
 */
export declare function verify(message: Uint8Array, signature: Uint8Array, publicKeyPem: string): boolean;
/**
 * 对称加密（使用 AES-256-GCM）
 * PSK: 预共享密钥
 */
export interface EncryptedData {
    ciphertext: Uint8Array;
    iv: Uint8Array;
    authTag: Uint8Array;
}
export declare function encrypt(plaintext: Uint8Array, psk: string): EncryptedData;
/**
 * 对称解密
 */
export declare function decrypt(data: EncryptedData, psk: string): Uint8Array | null;
/**
 * PSK 派生（基于密码短语 HKDF）
 */
export declare function derivePsk(passphrase: string, salt?: string): string;
/**
 * 生成临时会话密钥（用于握手后的通信）
 */
export declare function generateSessionKey(): string;
/**
 * 握手消息格式（Curve25519 风格）
 */
export interface HandshakeMessage {
    version: number;
    peerId: string;
    publicKey: string;
    signature: string;
    timestamp: number;
}
/**
 * 创建握手消息
 */
export declare function createHandshakeMessage(peerId: string, publicKey: string, privateKeyPem: string): HandshakeMessage;
/**
 * 验证握手消息
 */
export declare function verifyHandshakeMessage(msg: HandshakeMessage, publicKeyPem: string): boolean;
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
export declare function issueCertificate(subject: string, publicKey: string, privateKeyPem: string, validDays?: number): Certificate;
/**
 * 验证证书
 */
export declare function verifyCertificate(cert: Certificate, publicKeyPem: string): boolean;
/**
 * 白名单管理
 */
export declare class Whitelist {
    private allowedPeers;
    add(peerId: string): void;
    remove(peerId: string): void;
    contains(peerId: string): boolean;
    clear(): void;
    list(): string[];
}
//# sourceMappingURL=crypto.d.ts.map