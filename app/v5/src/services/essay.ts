/**
 * @fileoverview 作文批改服务模块 (Essay Service)
 * @description 提供作文批改相关的业务功能，支持纯文本批改和图片 OCR 批改。
 *              调用后端 LLM 服务对作文进行语法检查、评分和润色。
 */

import api from './api';
import type { EssayCorrectionResult } from '../types/essay';

export const EssayService = {
  /**
   * 文本作文批改
   * 
   * 直接提交作文文本内容进行批改。
   * 
   * @param {string} text - 作文文本内容
   * @param {string} language - 目标语言 (默认为 'english')
   * @returns {Promise<EssayCorrectionResult>} 批改结果 (包含评分、评语、修改建议)
   * @throws {Error} 如果批改失败
   */
  async correct(text: string, language: string = 'english'): Promise<EssayCorrectionResult> {
    const response = await api.post('/api/essay/correct', { text, language });
    const result = response as unknown as { success: boolean; data: EssayCorrectionResult; error?: string };
    
    if (result.success) {
      return result.data;
    }
    throw new Error(result.error || '批改失败');
  },

  /**
   * 图片作文批改 (OCR)
   * 
   * 上传作文图片，后端先进行 OCR 识别提取文字，再进行批改。
   * 
   * @param {string} imageBase64 - 图片的 Base64 字符串
   * @param {string} language - 目标语言 (默认为 'english')
   * @returns {Promise<EssayCorrectionResult>} 批改结果
   * @throws {Error} 如果 OCR 或批改失败
   */
  async correctOCR(imageBase64: string, language: string = 'english'): Promise<EssayCorrectionResult> {
    // 预处理：去除 Base64 前缀
    const cleanBase64 = imageBase64.includes(',') ? imageBase64.split(',')[1] : imageBase64;

    const response = await api.post('/api/essay/correct', { image: cleanBase64, language });
    const result = response as unknown as { success: boolean; data: EssayCorrectionResult; error?: string };

    if (result.success) {
      return result.data;
    }
    throw new Error(result.error || 'OCR 批改失败');
  }
};
