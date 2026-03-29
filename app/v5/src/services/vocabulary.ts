/**
 * @fileoverview 词汇服务模块 (Vocabulary Service)
 * @description 提供词汇查询相关的业务功能，包括文本查词和 OCR 图片查词。
 *              负责调用后端 API 并对返回的数据进行适配和类型转换。
 */

import api from './api';
import { AuthService } from './auth';
import type { VocabularyResult } from '../types/vocabulary';

function toVocabularyResult(params: {
  word: string;
  meaning?: string;
  example?: string;
  exampleTranslation?: string;
  definition?: string;
}): VocabularyResult {
  let meaning = String(params.meaning || '').trim();
  let example = String(params.example || '').trim();

  const definitionText = String(params.definition || '').trim();
  if ((!meaning || !example) && definitionText) {
    const lines = definitionText.split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
    for (const line of lines) {
      if (!meaning && line.startsWith('释义：')) {
        meaning = line.replace(/^释义：\s*/, '').trim();
      } else if (!example && line.startsWith('例句：')) {
        example = line.replace(/^例句：\s*/, '').trim();
      }
    }
    if (!meaning && lines.length > 0) meaning = lines[0];
    if (!example && lines.length > 1) example = lines[1];
  }

  const result: VocabularyResult = {
    word: params.word,
    definitions: [
      {
        meaning: meaning || '暂无',
        example: example || '',
      },
    ],
    meaning: meaning || '暂无',
  };

  if (params.exampleTranslation) {
    result.examples = [{ en: example || '', zh: String(params.exampleTranslation).trim() }];
  }

  return result;
}

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
    
    const response = await api.post('/v1/vocab/lookup', { term: word, source: 'manual' });
    const result = response as unknown as { term: string; definition: string };
    return toVocabularyResult({
      word: String(result.term || word),
      definition: String(result.definition || ''),
    });
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

    const response = await api.post('/v1/vocab/lookup-ocr', { image: cleanBase64, language: 'english' });
    const result = response as unknown as {
      term: string;
      ocr_text: string;
      meaning: string;
      example: string;
      example_translation?: string;
    };
    return toVocabularyResult({
      word: String(result.term || ''),
      meaning: String(result.meaning || ''),
      example: String(result.example || ''),
      exampleTranslation: String(result.example_translation || ''),
    });
  }
};
