/**
 * Softbus - ZeroMQ-based P2P Message Bus
 * Encryption & Identity (CurveZMQ-inspired)
 */
import * as crypto from 'crypto';
/**
 * 生成 Ed25519 密钥对
 */
export function generateKeyPair() {
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
        publicKey: publicKey.toString('base64'),
        privateKey: privateKey.toString('base64'),
    };
}
/**
 * PeerID 派生：基于公钥的 SHA256 哈希
 */
export function derivePeerId(publicKey) {
    const hash = crypto.createHash('sha256').update(publicKey).digest('hex');
    return hash.substring(0, 16); // 取前 16 字符作为 PeerID
}
/**
 * 数字签名（使用 Ed25519）
 */
export function sign(message, privateKeyPem) {
    const signer = crypto.createSign('SHA256');
    signer.update(message);
    // 将 PEM 格式私钥转换为 Node 可用格式
    const signature = signer.sign(privateKeyPem, 'binary');
    return new Uint8Array(Buffer.from(signature, 'binary'));
}
/**
 * 验证签名
 */
export function verify(message, signature, publicKeyPem) {
    try {
        const verifier = crypto.createVerify('SHA256');
        verifier.update(message);
        return verifier.verify(publicKeyPem, Buffer.from(signature));
    }
    catch {
        return false;
    }
}
export function encrypt(plaintext, psk) {
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
export function decrypt(data, psk) {
    try {
        const decipher = crypto.createDecipheriv('aes-256-gcm', Buffer.from(psk, 'hex'), data.iv);
        decipher.setAuthTag(data.authTag);
        const decrypted = Buffer.concat([
            decipher.update(data.ciphertext),
            decipher.final(),
        ]);
        return new Uint8Array(decrypted);
    }
    catch {
        return null;
    }
}
/**
 * PSK 派生（基于密码短语 HKDF）
 */
export function derivePsk(passphrase, salt = 'mmls-softbus') {
    const hkdf = crypto.hkdfSync('sha256', passphrase, salt, 'psk-key', 32);
    return hkdf.toString('hex');
}
/**
 * 生成临时会话密钥（用于握手后的通信）
 */
export function generateSessionKey() {
    return crypto.randomBytes(32).toString('hex');
}
/**
 * 创建握手消息
 */
export function createHandshakeMessage(peerId, publicKey, privateKeyPem) {
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
export function verifyHandshakeMessage(msg, publicKeyPem) {
    try {
        const payload = new TextEncoder().encode(`${msg.peerId}-${msg.publicKey}-${msg.timestamp}`);
        const signature = new Uint8Array(Buffer.from(msg.signature, 'base64'));
        return verify(payload, signature, publicKeyPem);
    }
    catch {
        return false;
    }
}
/**
 * 颁发自签名证书
 */
export function issueCertificate(subject, publicKey, privateKeyPem, validDays = 365) {
    const now = Date.now();
    const cert = {
        issuer: subject, // 自签
        subject,
        publicKey,
        signature: '',
        validFrom: now,
        validTo: now + validDays * 24 * 60 * 60 * 1000,
    };
    // 对证书内容签名
    const certPayload = new TextEncoder().encode(`${cert.issuer}-${cert.subject}-${cert.publicKey}-${cert.validFrom}-${cert.validTo}`);
    const signature = sign(certPayload, privateKeyPem);
    cert.signature = Buffer.from(signature).toString('base64');
    return cert;
}
/**
 * 验证证书
 */
export function verifyCertificate(cert, publicKeyPem) {
    const now = Date.now();
    if (now < cert.validFrom || now > cert.validTo) {
        return false; // 证书过期
    }
    const certPayload = new TextEncoder().encode(`${cert.issuer}-${cert.subject}-${cert.publicKey}-${cert.validFrom}-${cert.validTo}`);
    const signature = new Uint8Array(Buffer.from(cert.signature, 'base64'));
    return verify(certPayload, signature, publicKeyPem);
}
/**
 * 白名单管理
 */
export class Whitelist {
    allowedPeers = new Set();
    add(peerId) {
        this.allowedPeers.add(peerId);
    }
    remove(peerId) {
        this.allowedPeers.delete(peerId);
    }
    contains(peerId) {
        return this.allowedPeers.has(peerId);
    }
    clear() {
        this.allowedPeers.clear();
    }
    list() {
        return Array.from(this.allowedPeers);
    }
}
//# sourceMappingURL=crypto.js.map