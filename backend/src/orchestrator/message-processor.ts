/**
 * @fileoverview 消息处理器 (Message Processor)
 * 
 * 负责系统内部消息的预处理和验证逻辑。
 * 接收原始消息对象，执行格式验证、清洗和标准化，返回处理后的消息对象。
 * 
 * 主要功能：
 * 1. 消息处理 (Process)：验证并标准化消息
 * 2. 消息验证 (Validate)：检查消息格式的完整性
 * 
 * 待改进项：
 * 1. 实现实际的消息清洗逻辑 (如去除非法字符、格式转换)
 * 2. 添加消息类型注册机制，支持动态扩展消息处理器
 * 3. 增加消息处理的超时控制
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { Message } from '../shared/types';
import { logger } from '../utils/logger';

export class MessageProcessor {
  /**
   * 处理消息
   * 接收消息对象，执行验证和预处理，并返回处理后的消息对象
   * 
   * @param message 待处理的消息对象
   * @returns 处理后的消息对象
   * @throws Error 如果消息无效或处理失败
   */
  async process(message: Message): Promise<Message> {
    const startTime = Date.now();
    
    try {
      logger.debug(`Processing message: ${message.type} from ${message.sender}`);
      
      if (!this.validateMessage(message)) {
        throw new Error('Invalid message format');
      }

      // 智能内容识别与路由标记 (Content Recognition & Routing Tagging)
      // 根据消息内容自动推断目标服务主题
      if (message.type === 'image' || (message.payload && message.payload.image)) {
        logger.debug('Detected image content, routing to OCR service');
        message.topic = 'svc/ocr';
      } else if (message.type === 'audio' || (message.payload && message.payload.audio)) {
        logger.debug('Detected audio content, routing to ASR service');
        message.topic = 'svc/asr';
      }

      // 目前仅做透传，未来可在此处添加清洗/转换逻辑
      const processedMessage = { ...message };
      
      logger.debug(`Message processed successfully in ${Date.now() - startTime}ms`);
      return processedMessage;
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      logger.error(`Message processing failed: ${errorMessage}`);
      throw error;
    }
  }

  /**
   * 验证消息有效性
   * 检查消息是否包含必要的字段
   * 
   * @param message 待验证的消息对象
   * @returns 如果消息有效返回 true，否则返回 false
   */
  validateMessage(message: Message): boolean {
    // 宽松验证，确保基本字段存在
    return !!(
      message &&
      message.type
    );
  }
}
