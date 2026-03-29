/**
 * @fileoverview 作文批改服务模块 (Essay Service)
 * @description 提供作文批改相关的业务功能，支持纯文本批改和图片 OCR 批改。
 *              调用后端 LLM 服务对作文进行语法检查、评分和润色。
 */

import api from './api';
import type { EssayCorrectionResult } from '../types/essay';

function toEssayCorrectionResult(raw: any, originalText: string): EssayCorrectionResult {
  const result = (raw?.result && typeof raw.result === 'object') ? raw.result : raw;

  const total = Number(result?.score ?? result?.scores?.total ?? 0);
  const scores = result?.scores && typeof result.scores === 'object'
    ? result.scores
    : {
        vocabulary: Math.max(0, Math.min(100, Math.round(total))),
        grammar: Math.max(0, Math.min(100, Math.round(total))),
        fluency: Math.max(0, Math.min(100, Math.round(total))),
        logic: Math.max(0, Math.min(100, Math.round(total))),
        content: Math.max(0, Math.min(100, Math.round(total))),
        structure: Math.max(0, Math.min(100, Math.round(total))),
        total: Math.max(0, Math.min(100, Math.round(total))),
      };

  return {
    original: String(result?.original || originalText || ''),
    correction: String(result?.rewritten || result?.correction || ''),
    scores: {
      vocabulary: Number(scores.vocabulary ?? total ?? 0),
      grammar: Number(scores.grammar ?? total ?? 0),
      fluency: Number(scores.fluency ?? total ?? 0),
      logic: Number(scores.logic ?? total ?? 0),
      content: Number(scores.content ?? total ?? 0),
      structure: Number(scores.structure ?? total ?? 0),
      total: Number(scores.total ?? total ?? 0),
    },
    feedback: String(result?.feedback || ''),
    suggestions: Array.isArray(result?.suggestions) ? result.suggestions : [],
    questions: Array.isArray(result?.questions) ? result.questions : [],
    improvements: Array.isArray(result?.improvements) ? result.improvements : [],
    evaluation: String(result?.evaluation || ''),
  };
}

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
    const response = await api.post('/v1/essays/grade', { ocr_text: text, language }, { timeout: 60000 });
    return toEssayCorrectionResult(response, text);
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

    const response = await api.post('/v1/essays/grade-ocr', { image: cleanBase64, language }, { timeout: 60000 });
    return toEssayCorrectionResult(response, '');
  }
};
