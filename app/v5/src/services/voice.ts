/**
 * @fileoverview 语音业务服务模块 (Voice Service)
 * @description 提供语音对话相关的 HTTP 接口调用，主要用于会话初始化和 Prompt 生成。
 *              注意：实时的语音流传输通过 WebSocket (voice-socket.ts) 处理，而非本模块。
 */

import api from './api';

/** 语音 Prompt 生成结果接口 */
export interface VoicePromptResult {
  success: boolean;
  /** 生成的系统提示词，用于指导 AI 的角色扮演 */
  systemPrompt: string;
}

/** 语音会话启动结果接口 */
export interface VoiceStartResult {
  success: boolean;
  /** AI 的开场白文本 */
  openingText: string;
  /** AI 开场白的音频数据（base64(wav bytes)） */
  openingAudio: string; 
}

export const VoiceService = {
  /**
   * 生成系统提示词 (System Prompt)
   * 
   * 根据用户选择的场景和语言，调用后端生成对应的 AI 角色设定提示词。
   * 
   * @param {string} scenario - 对话场景 ID (如 'daily', 'business')
   * @param {string} language - 目标语言代码 (如 'zh-CN', 'en-US')
   * @returns {Promise<string>} 生成的系统提示词
   * @throws {Error} 如果生成失败
   */
  async generatePrompt(scenario: string, language: string): Promise<string> {
    const response = await api.post('/api/voice/generate-prompt', { scenario, language });
    const result = response as unknown as VoicePromptResult;
    if (result.success) {
      return result.systemPrompt;
    }
    throw new Error('生成提示词失败');
  },

  /**
   * 启动语音会话
   * 
   * 向后端发送系统提示词，初始化一个新的语音会话上下文。
   * 后端会返回 AI 的开场白（文本和音频）。
   * 
   * @param {string} systemPrompt - 系统提示词
   * @returns {Promise<VoiceStartResult>} 会话启动结果
   * @throws {Error} 如果启动失败
   */
  async startSession(systemPrompt: string): Promise<VoiceStartResult> {
    const response = await api.post('/api/voice/start', { systemPrompt });
    const result = response as unknown as VoiceStartResult;
    if (result.success) {
      return result;
    }
    throw new Error('启动会话失败');
  }
};
