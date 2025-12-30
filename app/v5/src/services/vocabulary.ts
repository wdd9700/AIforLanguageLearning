/**
 * @fileoverview 词汇服务模块 (Vocabulary Service)
 * @description 提供词汇查询相关的业务功能，包括文本查词和 OCR 图片查词。
 *              负责调用后端 API 并对返回的数据进行适配和类型转换。
 */

import api from './api';
import { AuthService } from './auth';
import type { VocabularyResult, OCRResult } from '../types/vocabulary';

export const VocabularyService = {
  /**
   * 词汇查询 (Text Lookup)
   * 
   * 调用后端 LLM 服务查询指定单词的详细释义、例句、发音等信息。
   * 
   * @param {string} word - 待查询的单词或短语
   * @returns {Promise<VocabularyResult>} 查询结果对象
   * @throws {Error} 如果查询失败或后端返回错误信息
   */
  async query(word: string): Promise<VocabularyResult> {
    // 确保用户已登录
    await AuthService.ensureLogin();
    
    // 发送 POST 请求
    const response = await api.post<{ success: boolean; data: VocabularyResult }>('/api/query/vocabulary', { word });
    
    // 由于 Axios 拦截器已经返回了 response.data，这里我们需要将其断言为后端返回的 JSON 结构
    const result = response as unknown as { success: boolean; data: VocabularyResult; error?: string };
    
    if (result.success) {
      return result.data;
    }
    throw new Error(result.error || '查询失败');
  },

  /**
   * OCR 图片查词 (Image Lookup)
   * 
   * 上传图片 Base64 数据，后端进行 OCR 文字识别并查询识别到的单词释义。
   * 
   * @param {string} imageBase64 - 图片的 Base64 字符串 (可包含或不包含 data URI 前缀)
   * @returns {Promise<VocabularyResult>} 查询结果对象
   * @throws {Error} 如果 OCR 识别失败或查询出错
   */
  async queryOCR(imageBase64: string): Promise<VocabularyResult> {
    // 预处理：如果存在 data:image/png;base64, 前缀，则去除，只保留 Base64 数据部分
    const cleanBase64 = imageBase64.includes(',') ? imageBase64.split(',')[1] : imageBase64;

    const response = await api.post('/api/query/ocr', { image: cleanBase64 });
    const result = response as unknown as { success: boolean; data: OCRResult | { explanation: VocabularyResult }; error?: string };

    if (result.success) {
      // 适配后端可能返回的不同数据结构
      // 结构 1: data.explanation 是一个完整的 VocabularyResult 对象
      if ('explanation' in result.data && result.data.explanation) {
         if (typeof result.data.explanation === 'object' && 'word' in result.data.explanation) {
             return result.data.explanation as VocabularyResult;
         }
      }
      
      // 如果无法解析出结构化数据，可能需要在此处进行回退处理或抛出错误
      // 目前逻辑保持与旧版一致，尽量尝试提取
      throw new Error('无法解析 OCR 返回的数据结构');
    }
    throw new Error(result.error || 'OCR 查询失败');
  }
};
