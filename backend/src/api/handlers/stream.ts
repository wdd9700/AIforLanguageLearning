/**
 * @fileoverview WebSocket 流处理器 (Stream Handler)
 * @description
 * 该文件实现了复杂的实时语音对话流处理逻辑，是语音对话功能的核心后端组件。
 * 
 * 核心功能：
 * 1. 全双工通信：通过 WebSocket 接收客户端音频流，同时推送 ASR、LLM 和 TTS 的实时结果
 * 2. 服务编排：协调 ASR（语音转文本）、LLM（生成回复）和 TTS（文本转语音）三个服务的串行工作流
 * 3. 上下文管理：维护对话历史 (History)，支持多轮对话
 * 4. 场景配置：支持动态切换对话场景 (Scenario) 和系统提示词 (System Prompt)
 * 5. 流式处理：
 *    - ASR 实时返回转录文本
 *    - LLM 流式生成 Token
 *    - TTS 接收 LLM 的流式输出并实时合成音频
 * 
 * 流程：
 * Client Audio -> ASR Process -> Text -> LLM API (Stream) -> Text Chunk -> TTS Process -> Audio -> Client
 * 
 * 待改进项：
 * - [ ] 引入状态机 (State Machine) 管理复杂的对话状态 (Listening, Thinking, Speaking)
 * - [ ] 优化打断 (Barge-in) 机制，实现更自然的对话交互
 * - [ ] 支持根据角色动态切换 TTS 音色
 * - [ ] 收集端到端延迟 (Latency) 指标用于性能优化
 * - [ ] 移除硬编码的 LLM Endpoint 和 Model 名称，统一从配置加载
 * - [ ] 移除硬编码的 TTS Prompt 音频路径
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import WebSocket from 'ws';
import { ServiceManager } from '../../managers/service-manager';
import { SessionManager } from '../../managers/session-manager';
import { createLogger } from '../../utils/logger';
import { verifyAccessToken } from '../../auth/jwt';
import { ChildProcess } from 'child_process';
import axios from 'axios';
import { config } from '../../config/env';
import { PROMPTS } from '../../config/prompts';

const logger = createLogger('StreamHandler');

interface WSMessage {
  type: 'start' | 'stop' | 'config' | 'interrupt' | 'page_mounted';
  data?: any;
  token?: string;
}

export function createStreamHandler(
  serviceManager: ServiceManager,
  sessionManager: SessionManager
): (ws: WebSocket, req: any) => void {
  return (ws: WebSocket, req: any) => {
    let asrProcess: ChildProcess | null = null;
    let ttsProcess: ChildProcess | null = null;
    let isSessionActive = false;
    let abortController: AbortController | null = null; // 用于取消正在进行的 LLM 请求
    
    // LLM 流式输出缓冲区
    let llmBuffer = "";
    
    let asrCleanup: (() => void) | null = null;
    let ttsCleanup: (() => void) | null = null;
    
    // 会话配置
    let currentScenario = 'daily'; // 默认场景
    let currentLanguage = 'zh'; // 默认语言
    let customSystemPrompt: string | null = null;
    
    // 上下文管理
    const MAX_HISTORY = 20;
    let history: Array<{ role: string, content: string }> = [];

    logger.info('WebSocket connection established');

    // 监听 WebSocket 消息
    ws.on('message', async (data: WebSocket.Data, isBinary: boolean) => {
      try {
        // 处理二进制音频数据 (客户端 -> ASR)
        if (isBinary) {
          if (isSessionActive && asrProcess && asrProcess.stdin) {
            asrProcess.stdin.write(data as Buffer);
          }
          return;
        }

        // 处理 JSON 控制消息
        const message: WSMessage = JSON.parse(data.toString());

        if (message.type === 'config') {
            // 更新会话配置
            if (message.data?.scenario) {
                currentScenario = message.data.scenario;
                logger.info({ currentScenario }, "Session scenario updated");
            }
            if (message.data?.systemPrompt) {
                customSystemPrompt = message.data.systemPrompt;
                logger.info("Custom system prompt updated");
            }
        } else if (message.type === 'start') {
            logger.info("Starting AI Session...");
            
            // 启动时可携带配置
            if ((message as any).config?.scenario) {
                 currentScenario = (message as any).config.scenario;
            }
            if ((message as any).config?.language) {
                 // 映射前端语言代码 (如 'zh-CN') 到后端代码 (如 'zh')
                 const langMap: Record<string, string> = {
                     'zh-CN': 'zh',
                     'en-US': 'en',
                     'ja-JP': 'ja'
                 };
                 currentLanguage = langMap[(message as any).config.language] || 'zh';
            }
            
            logger.info({ currentScenario, currentLanguage }, "Session initialized");

            isSessionActive = true;
            
            // 1. 启动 ASR 服务
            asrProcess = serviceManager.asr.start();
            if (asrCleanup) asrCleanup();
            asrCleanup = setupASRListeners(asrProcess, ws, (text) => triggerLLM(text));
            
            // 2. 启动 TTS 服务
            ttsProcess = serviceManager.tts.start();
            if (ttsCleanup) ttsCleanup();
            ttsCleanup = setupTTSListeners(ttsProcess, ws);
            
            ws.send(JSON.stringify({ type: 'status', status: 'ready' }));
        } else if (message.type === 'stop') {
            // 停止会话
            isSessionActive = false;
            if (abortController) abortController.abort();
            ws.send(JSON.stringify({ type: 'status', status: 'stopped' }));
        } else if (message.type === 'interrupt') {
            // 打断当前对话
            logger.info("Interruption signal received");
            if (abortController) {
                abortController.abort();
                abortController = null;
            }
            // TODO: 清空 TTS 缓冲区 (如果支持)
        } else if (message.type === 'page_mounted') {
            // 页面加载事件，用于按需启动服务
            const page = message.data?.page;
            logger.info({ page }, "Client page mounted");
            
            if (page === 'voice-dialogue' || page === 'voice-dialogue-v5') {
                serviceManager.asr.start();
                serviceManager.tts.start();
                ws.send(JSON.stringify({ type: 'service_status', services: { asr: 'running', tts: 'running' } }));
            } else {
                // 离开语音页面时停止服务以节省资源
                serviceManager.asr.shutdown();
                serviceManager.tts.shutdown();
                ws.send(JSON.stringify({ type: 'service_status', services: { asr: 'stopped', tts: 'stopped' } }));
            }
        }

      } catch (error: any) {
        logger.error({ error: error.message }, 'WebSocket message handling failed');
      }
    });

    ws.on('close', () => {
      logger.info('WebSocket connection closed');
      isSessionActive = false;
      if (abortController) abortController.abort();
      if (asrCleanup) asrCleanup();
      if (ttsCleanup) ttsCleanup();
    });

    // 辅助函数: 触发 LLM 生成
    async function triggerLLM(text: string) {
        if (!text.trim()) return;
        
        // 取消上一次未完成的请求
        if (abortController) abortController.abort();
        abortController = new AbortController();
        
        logger.info({ text }, "ASR Final Result -> Triggering LLM");
        ws.send(JSON.stringify({ type: 'llm_start', prompt: text }));

        try {
            // 调用 LLM 服务 (流式)
            const modelName = (config.services.llm.models as any).conversation || "qwen3-vl-8b-instruct";
            const endpoint = config.services.llm.endpoint || 'http://localhost:1234/v1/chat/completions';
            
            // 确保 endpoint 格式正确
            const url = endpoint.endsWith('/v1/chat/completions') ? endpoint : `${endpoint}/v1/chat/completions`;

            // 获取系统提示词 (System Prompt)
            let systemPrompt = PROMPTS.dialogue.default;
            
            if (customSystemPrompt) {
                systemPrompt = customSystemPrompt;
            } else if (currentScenario in PROMPTS.dialogue) {
                systemPrompt = (PROMPTS.dialogue as any)[currentScenario];
                logger.info({ currentScenario }, "Using scenario prompt");
            } else {
                logger.warn({ currentScenario }, "Scenario prompt not found, using default");
            }

            // 更新对话历史
            history.push({ role: "user", content: text });
            if (history.length > MAX_HISTORY) {
                history = history.slice(history.length - MAX_HISTORY);
            }

            const messages = [
                { role: "system", content: systemPrompt },
                ...history
            ];

            const response = await axios.post(url, {
                model: modelName,
                messages: messages,
                stream: true
            }, {
                responseType: 'stream',
                signal: abortController.signal
            });

            const stream = response.data;
            let buffer = "";
            let fullResponse = "";
            
            stream.on('data', (chunk: Buffer) => {
                const lines = chunk.toString().split('\n');
                for (const line of lines) {
                    if (line.trim() === '') continue;
                    if (line.trim() === 'data: [DONE]') continue;
                    if (line.startsWith('data: ')) {
                        try {
                            const json = JSON.parse(line.substring(6));
                            const content = json.choices[0]?.delta?.content || "";
                            if (content) {
                                buffer += content;
                                fullResponse += content;
                                ws.send(JSON.stringify({ type: 'llm_token', content }));
                                
                                // 检测句子结束，发送给 TTS
                                // 简单的标点符号检测
                                if (/[.!?。！？\n]/.test(content)) {
                                    sendToTTS(buffer);
                                    buffer = "";
                                }
                            }
                        } catch (e) {
                            // ignore parse error
                        }
                    }
                }
            });
            
            stream.on('end', () => {
                // 发送剩余的缓冲区内容
                if (buffer.trim()) {
                    sendToTTS(buffer);
                }
                // 将助手回复添加到历史记录
                if (fullResponse.trim()) {
                    history.push({ role: "assistant", content: fullResponse });
                    if (history.length > MAX_HISTORY) {
                        history = history.slice(history.length - MAX_HISTORY);
                    }
                }
                ws.send(JSON.stringify({ type: 'llm_end' }));
            });

        } catch (e: any) {
            logger.error({ error: e.message }, "LLM Request Failed");
            ws.send(JSON.stringify({ type: 'error', error: "LLM failed" }));
        }
    }

    // 发送文本到 TTS 服务
    function sendToTTS(text: string) {
        if (!ttsProcess || !ttsProcess.stdin) return;
        if (!text.trim()) return;
        
        logger.info({ text, lang: currentLanguage }, "Sending to TTS");
        const req = {
            text: text,
            lang: currentLanguage, 
            prompt_wav: config.services.tts.promptAudioPath
        };
        ttsProcess.stdin.write(JSON.stringify(req) + "\n");
    }
  };
}

// 设置 ASR 进程监听器
function setupASRListeners(proc: ChildProcess, ws: WebSocket, onFinalText: (text: string) => void) {
    const dataListener = (data: any) => {
        const lines = data.toString().split('\n');
        for (const line of lines) {
            if (!line.trim()) continue;
            try {
                const event = JSON.parse(line);
                if (event.type === 'transcription') {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: 'asr_result', ...event }));
                        onFinalText(event.text);
                    }
                } else if (event.type === 'vad_start') {
                    if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'vad_status', status: 'speaking' }));
                } else if (event.type === 'vad_end') {
                    if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'vad_status', status: 'silence' }));
                }
            } catch (e) {
                // ignore
            }
        }
    };

    proc.stdout?.on('data', dataListener);
    
    return () => {
        proc.stdout?.removeListener('data', dataListener);
    };
}

// 设置 TTS 进程监听器
function setupTTSListeners(proc: ChildProcess, ws: WebSocket) {
    const dataListener = (data: any) => {
        const lines = data.toString().split('\n');
        for (const line of lines) {
            if (!line.trim()) continue;
            try {
                const event = JSON.parse(line);
                if (event.type === 'audio') {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: 'tts_audio', data: event.data }));
                    }
                }
            } catch (e) {
                // ignore
            }
        }
    };

    proc.stdout?.on('data', dataListener);

    return () => {
        proc.stdout?.removeListener('data', dataListener);
    };
}

