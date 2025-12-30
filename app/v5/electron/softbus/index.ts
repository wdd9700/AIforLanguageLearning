/**
 * @fileoverview 软总线模块入口 (Softbus Module Entry)
 * @description
 * 该模块统一导出了软总线系统的所有核心组件和接口。
 * 
 * 包含组件：
 * - 客户端 SDK (zmq-sdk.ts)
 * - 加密与安全 (crypto.ts)
 * - 协议编解码 (protocol.ts)
 * - 类型定义 (types.ts)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

export { SoftbusClient, Stream } from './zmq-sdk.js';
export { generateKeyPair, derivePeerId, sign, verify, encrypt, decrypt, derivePsk, generateSessionKey, createHandshakeMessage, verifyHandshakeMessage, issueCertificate, verifyCertificate, Whitelist, type EncryptedData, type HandshakeMessage, type Certificate } from './crypto.js';
export { encodeMessage, decodeMessage, encodeVarint, decodeVarint, validateMessageVersion, generateMsgId, generateTraceId, createErrorMessage, parseErrorMessage } from './protocol.js';
export * from './types.js';
