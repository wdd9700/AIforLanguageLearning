/**
 * @fileoverview 简单音频流处理器 (Simple Stream Handler)
 * @description
 * 该文件实现了一个简化的音频流处理逻辑，用于处理一次性的语音交互请求。
 * 
 * 核心流程 (Pipeline)：
 * 1. 接收音频：从 WebSocket 消息中获取 Base64 编码的音频数据
 * 2. ASR 识别：调用 ASR 服务将语音转换为文本
 * 3. LLM 生成：将识别出的文本作为 Prompt 发送给 LLM，获取回复
 * 4. TTS 合成：将 LLM 的回复转换为语音
 * 5. 实时反馈：在每个阶段（ASR 结果、LLM 回复、TTS 音频）完成后立即通过 WebSocket 推送给客户端
 * 
 * 适用场景：
 * - 简单的语音问答
 * - 不需要上下文记忆的单轮对话
 * - 测试和调试语音链路
 * 
 * 待改进项：
 * - [ ] 增加 WebSocket 连接断开的异常处理
 * - [ ] 支持客户端指定 TTS 音色参数
 * - [ ] 为 LLM 请求增加超时控制
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import WebSocket from 'ws';
import { ServiceManager } from '../../managers/service-manager';
import { createLogger } from '../../utils/logger';

const logger = createLogger('SimpleStreamHandler');

/**
 * 处理简单的音频流消息 (ASR -> LLM -> TTS)
 * 这种模式不需要复杂的会话管理，适用于一次性的交互
 * 
 * 流程：
 * 1. 接收音频数据
 * 2. 调用 ASR 服务进行语音转文字
 * 3. 将识别结果发送给 LLM 获取回复
 * 4. 调用 TTS 服务将回复转换为语音
 * 5. 将各阶段结果实时推送给客户端
 * 
 * @param ws WebSocket 连接实例
 * @param message 接收到的消息对象
 * @param serviceManager 服务管理器实例
 */
export async function handleSimpleAudioMessage(
  ws: WebSocket, 
  message: any, 
  serviceManager: ServiceManager
): Promise<void> {
  const audio = message.data;
  if (!audio) {
    ws.send(JSON.stringify({ type: 'error', data: { message: 'Missing audio data' } }));
    return;
  }

  // 将 Base64 音频转换为 Buffer
  const audioBuffer = Buffer.from(audio, 'base64');
  logger.info({ size: audioBuffer.length }, 'Processing audio stream');

  try {
    // Step 1: ASR (语音转文字)
    logger.debug('Invoking ASR service...');
    const asrResult = await serviceManager.asr.invoke(audioBuffer);
    const transcription = asrResult.text.trim();
    
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'asr_result',
        data: { text: transcription }
      }));
    }
    logger.info({ transcription }, 'ASR completed');

    // Step 2: LLM (大语言模型生成回复)
    logger.debug('Invoking LLM service...');
    const llmResult = await serviceManager.llm.invoke({
      prompt: transcription,
      task: 'conversation',
      temperature: 0.7
    });
    
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'llm_result',
        data: { text: llmResult.response }
      }));
    }
    logger.info({ response: llmResult.response.substring(0, 50) }, 'LLM completed');

    // Step 3: TTS (文字转语音)
    logger.debug('Invoking TTS service...');
    const ttsResult = await serviceManager.tts.invoke(llmResult.response, {
      voice: 'default',
      speed: 1.0
    });
    
    const audioBase64 = ttsResult.audio.toString('base64');
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'tts_result',
        data: { 
          text: llmResult.response,
          audio: audioBase64
        }
      }));
    }
    logger.info({ audioSize: ttsResult.audio.length }, 'TTS completed');

  } catch (serviceError: any) {
    logger.error({ error: serviceError.message }, 'Service error');
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'error',
        data: { message: serviceError.message }
      }));
    }
  }
}
