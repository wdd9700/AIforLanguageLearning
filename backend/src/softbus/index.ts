/**
 * @fileoverview 软总线 (Softbus) 统一导出入口
 * 
 * 聚合导出 SDK 客户端、加密模块、协议处理和类型定义。
 * 作为软总线模块的公共 API 接口，供外部模块调用。
 * 
 * 导出内容：
 * 1. 核心客户端：SoftbusClient, Stream
 * 2. 安全模块：密钥管理、加解密、签名验证、证书管理
 * 3. 协议模块：消息编解码、ID 生成、错误处理
 * 4. 类型定义：所有共享的接口和类型
 * 
 * 待改进项：
 * 1. 添加统一的配置加载器，支持从文件或环境变量加载软总线配置
 * 2. 导出更多的工具函数和辅助类
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

// 导出核心客户端和流对象
export { SoftbusClient, Stream } from './zmq-sdk';

// 导出加密与安全相关功能
export { 
  generateKeyPair, 
  derivePeerId, 
  sign, 
  verify, 
  encrypt, 
  decrypt, 
  derivePsk, 
  generateSessionKey, 
  createHandshakeMessage, 
  verifyHandshakeMessage, 
  issueCertificate, 
  verifyCertificate, 
  Whitelist, 
  type EncryptedData, 
  type HandshakeMessage, 
  type Certificate 
} from './crypto';

// 导出协议编解码与工具函数
export { 
  encodeMessage, 
  decodeMessage, 
  encodeVarint, 
  decodeVarint, 
  validateMessageVersion, 
  generateMsgId, 
  generateTraceId, 
  createErrorMessage, 
  parseErrorMessage 
} from './protocol';

// 导出所有类型定义
export * from './types';
