/**
 * Softbus 导出接口（统一入口）
 */
export { SoftbusClient, Stream } from './zmq-sdk.js';
export { generateKeyPair, derivePeerId, sign, verify, encrypt, decrypt, derivePsk, generateSessionKey, createHandshakeMessage, verifyHandshakeMessage, issueCertificate, verifyCertificate, Whitelist, type EncryptedData, type HandshakeMessage, type Certificate } from './crypto.js';
export { encodeMessage, decodeMessage, encodeVarint, decodeVarint, validateMessageVersion, generateMsgId, generateTraceId, createErrorMessage, parseErrorMessage } from './protocol.js';
export * from './types.js';
//# sourceMappingURL=index.d.ts.map