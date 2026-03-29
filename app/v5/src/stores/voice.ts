/**
 * @fileoverview 语音对话状态管理 (Voice Store)
 * @description 管理语音对话页面的核心业务逻辑和状态。
 *              负责协调 WebSocket 通信、音频录制/播放、对话历史记录以及 UI 状态更新。
 */

import { defineStore } from 'pinia';
import { ref } from 'vue';
import { voiceSocket } from '../services/voice-socket';
import { audioManager } from '../services/audio-manager';
import { ConfigService } from '../services/config';

export const useVoiceStore = defineStore('voice', () => {
  // ============ 状态定义 ============
  
  /** 是否正在录音 (用户正在说话) */
  const isRecording = ref(false);
  /** 是否正在处理中 (等待 AI 响应) */
  const isProcessing = ref(false);
  /** AI 是否正在说话 (播放音频中) */
  const isSpeaking = ref(false);
  /** WebSocket 连接状态 (响应式引用) */
  const isConnected = voiceSocket.isConnected;
  
  /** 当前选择的语言 */
  const currentLanguage = ref('zh-CN');
  /** 当前选择的对话场景 */
  const currentScenario = ref('daily');
  
  /** 状态栏显示的文本 */
  const statusText = ref('就绪');
  /** 状态栏显示的类型 (决定颜色和图标) */
  const statusType = ref<'success' | 'processing' | 'listening' | 'speaking' | 'error'>('success');

  /** 对话历史记录列表 */
  const currentDialogue = ref<Array<{ role: 'user' | 'assistant', content: string }>>([]);

  // ws-v1 连接上下文
  const sessionId = ref(`desktop_${Math.random().toString(16).slice(2)}`);
  const conversationId = ref(`conv_${Date.now().toString(16)}`);
  const currentRequestId = ref<string | null>(null);
  const wsV1PreferBinary = ref(true);
  const autoCaptureEnabled = ref(false);
  const speechThreshold = ref(420);

  // Ensure we only register one WS message handler.
  let wsUnsubscribe: (() => void) | null = null;
  let hasInitialized = false;

  // ============ 核心方法 ============

  /**
   * 初始化语音服务
   * 建立 WebSocket 连接并注册消息监听器。
   */
  const init = () => {
    // 注册一次消息处理器（重复注册会导致消息被处理多次）
    if (hasInitialized) return;
    hasInitialized = true;
    wsUnsubscribe = voiceSocket.onMessage(handleMessage);
    void ensureConnectedWsV1();
  };

  const ensureConnectedWsV1 = async () => {
    if (isConnected.value) return;
    try {
      const cfg: any = await ConfigService.getConfig();
      let backendUrl = String(cfg?.backend?.wsUrl || cfg?.backendUrl || 'localhost:8012');
      // Guard: avoid accidentally connecting to the frontend dev server (e.g. localhost:8000).
      try {
        const host = String(window?.location?.host || '');
        if (backendUrl === host || /:(8000)\b/.test(backendUrl)) {
          backendUrl = 'localhost:8012';
        }
      } catch {}
      voiceSocket.connectWsV1({
        backendUrl,
        sessionId: sessionId.value,
        conversationId: conversationId.value
      });
    } catch (e) {
      console.warn('ws-v1 connect failed, falling back to legacy connect', e);
      voiceSocket.connect();
    }
  };

  const waitForConnected = async (timeoutMs: number = 5000) => {
    if (isConnected.value) return;
    const start = Date.now();
    while (!isConnected.value) {
      if (Date.now() - start > timeoutMs) throw new Error('WebSocket connect timeout');
      await new Promise((r) => setTimeout(r, 50));
    }
  };

  /**
   * 添加一条新的对话消息
   * @param role - 角色 ('user' 或 'assistant')
   * @param content - 消息内容
   */
  const addMessage = (role: 'user' | 'assistant', content: string) => {
    currentDialogue.value.push({ role, content });
  };

  /**
   * 追加内容到最后一条 AI 消息 (用于流式输出)
   * @param token - 新生成的文本片段
   */
  const appendToLastAssistantMessage = (token: string) => {
    const lastMsg = currentDialogue.value[currentDialogue.value.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.content += token;
    } else {
      addMessage('assistant', token);
    }
  };

  /**
   * 处理 WebSocket 接收到的消息
   * 根据消息类型分发到不同的处理逻辑。
   */
  const handleMessage = (msg: any) => {
    // ws-v1 (backend_fastapi) event envelope: {type, seq, ts, session_id, conversation_id, request_id, payload}
    if (msg && typeof msg.type === 'string' && msg.type === msg.type.toUpperCase()) {
      const t = msg.type;
      const payload = msg.payload || {};
      const rid = String(msg.request_id || '');

      switch (t) {
        case 'TASK_STARTED': {
          // Ignore connection-level TASK_STARTED({message:connected})
          if (payload?.task === 'voice_audio') {
            setStatus('正在聆听...', 'listening');
          }
          return;
        }
        case 'ASR_PARTIAL': {
          if (payload?.text) {
            setStatus(`识别中: ${String(payload.text)}`, 'listening');
          }
          return;
        }
        case 'ASR_FINAL': {
          const text = String(payload?.text || '');
          if (text) addMessage('user', text);
          setStatus(text ? `识别: ${text}` : '识别完成', 'processing');
          isProcessing.value = true;
          return;
        }
        case 'LLM_TOKEN': {
          const delta = String(payload?.text || '');
          if (delta) {
            isProcessing.value = true;
            appendToLastAssistantMessage(delta);
          }
          return;
        }
        case 'LLM_RESULT': {
          // Fallback: if server didn't stream tokens, use the final markdown/text.
          const markdown = String(payload?.markdown || payload?.text || '');
          if (markdown) {
            const lastMsg = currentDialogue.value[currentDialogue.value.length - 1];
            if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
              lastMsg.content = markdown;
            } else if (!lastMsg || lastMsg.role !== 'assistant') {
              addMessage('assistant', markdown);
            }
          }
          setStatus('正在合成语音...', 'processing');
          isProcessing.value = true;
          return;
        }
        case 'TTS_CHUNK': {
          const b64 = String(payload?.data_b64 || '');
          if (b64) {
            setStatus('正在回复...', 'speaking');
            isSpeaking.value = true;
            isProcessing.value = false;
            // ws-v1 sends wav bytes
            void audioManager.playWavChunk(b64);
          }
          return;
        }
        case 'TASK_ABORTED': {
          if (rid && rid === currentRequestId.value) {
            audioManager.stopPlayback();
            isSpeaking.value = false;
            isProcessing.value = false;
            currentRequestId.value = null;
            setStatus('已打断', 'success');
          }
          return;
        }
        case 'TASK_FINISHED': {
          if (rid && rid === currentRequestId.value) {
            isProcessing.value = false;
            currentRequestId.value = null;
            // We don't have a precise audio-ended callback; best-effort clear UI state when task completes.
            isSpeaking.value = false;
            if ((payload?.ok ?? true) === false) {
              setStatus('任务已结束（取消/失败）', 'error');
            } else if (payload?.asr_only) {
              setStatus('完成', 'success');
            } else {
              setStatus('完成', 'success');
            }
          }
          return;
        }
        case 'ERROR': {
          const message = String(payload?.message || 'unknown error');
          setStatus(`错误: ${message}`, 'error');
          isProcessing.value = false;
          return;
        }
        default:
          return;
      }
    }

    switch (msg.type) {
      case 'vad_status':
        // VAD (语音活动检测) 状态变更
        if (msg.status === 'speaking') {
          setStatus('检测到语音', 'listening');
          // 用户开始说话时，打断 AI 的播放
          audioManager.stopPlayback();
          voiceSocket.send({ type: 'interrupt' });
          isSpeaking.value = false;
        } else {
          setStatus('语音结束，处理中...', 'processing');
        }
        break;
      case 'asr_result':
        // 收到语音转写结果
        setStatus(`识别: ${msg.text}`, 'success');
        addMessage('user', msg.text);
        break;
      case 'llm_token':
        // 收到 LLM 生成的文本片段 (流式)
        appendToLastAssistantMessage(msg.content);
        break;
      case 'tts_audio':
        // 收到 TTS 生成的音频分片
        if (msg.data) {
          setStatus('正在回复...', 'speaking');
          isSpeaking.value = true;
          isProcessing.value = false;
          audioManager.playChunk(msg.data);
        }
        break;
      case 'error':
        // 收到错误消息
        setStatus(`错误: ${msg.message}`, 'error');
        isProcessing.value = false;
        break;
    }
  };

  /**
   * 更新状态栏显示
   * @param text - 状态文本
   * @param type - 状态类型
   */
  const setStatus = (text: string, type: 'success' | 'processing' | 'listening' | 'speaking' | 'error') => {
    statusText.value = text;
    statusType.value = type;
  };

  /**
   * 启动自定义会话
   * 
   * 初始化一个新的会话上下文，设置语言和提示词，并播放开场白。
   * 
   * @param config - 会话配置对象
   */
  const startCustomSession = async (config: { systemPrompt: string; openingText: string; openingAudio: string; language: string }) => {
    // Ensure WS handler is registered before any server events arrive.
    init();
    if (!isConnected.value) {
      await ensureConnectedWsV1();
    }

    // 重置状态
    currentDialogue.value = [];
    currentLanguage.value = config.language;
    autoCaptureEnabled.value = true;
    
    // 添加开场白消息
    addMessage('assistant', config.openingText);
    
    // 播放开场白音频
    if (config.openingAudio) {
      isSpeaking.value = true;
      setStatus('正在回复...', 'speaking');
      // openingAudio uses base64(wav bytes)
      void audioManager.playWavChunk(config.openingAudio).finally(() => {
        // 这是“开场白”本地播放，不会收到 TASK_FINISHED；需要自行复位。
        if (!isRecording.value && !isProcessing.value) {
          isSpeaking.value = false;
          setStatus('就绪', 'success');
        }
      });
    }

    // ws-v1: 写入对话上下文（system prompt），供后端在 LLM 生成时使用。
    if (voiceSocket.isWsV1()) {
      const ctxRid = `ctx_${Date.now().toString(16)}`;
      voiceSocket.sendWsV1Event(
        'CONTEXT_SET',
        {
          system_prompt: config.systemPrompt,
          language: config.language
        },
        ctxRid
      );
    } else {
      // legacy-stream 才发送 init_session
      voiceSocket.send({
        type: 'init_session',
        config: {
          systemPrompt: config.systemPrompt,
          language: config.language
        }
      });
    }

    // 会话启动后直接进入“自动聆听”模式。
    await startRecording();
  };

  /**
   * 停止会话
   * 停止录音，发送停止指令，清空对话记录。
   */
  const stopSession = () => {
    stopRecording();
    if (!voiceSocket.isWsV1()) {
      voiceSocket.send({ type: 'stop_session' });
    }
    currentDialogue.value = [];
    setStatus('就绪', 'success');

    if (wsUnsubscribe) {
      wsUnsubscribe();
      wsUnsubscribe = null;
      hasInitialized = false;
    }
  };

  /**
   * 开始录音
   * 启动音频管理器并开始流式传输音频数据。
   */
  const startRecording = async () => {
    // Ensure WS handler is registered before any server events arrive.
    init();
    if (!isConnected.value) {
      await ensureConnectedWsV1();
      await waitForConnected(6000);
    }

    try {
      isRecording.value = true;
      autoCaptureEnabled.value = true;
      setStatus('正在聆听...', 'listening');
      
      // 持续录音：检测到语音能量后自动创建 request，并交给后端 VAD 自动收句。
      await audioManager.startRecording((data) => {
        if (!isRecording.value || !autoCaptureEnabled.value) {
          return;
        }

        const rms = calcRms(data);

        // 没有进行中的语音请求时，只有检测到明确语音才发起新请求。
        if (!currentRequestId.value && rms >= speechThreshold.value) {
          const rid = `voice_${Date.now().toString(16)}`;
          currentRequestId.value = rid;

          // barge-in: 本地立即停止旧播报，随后后端也会基于新请求触发中断逻辑。
          audioManager.stopPlayback();
          isSpeaking.value = false;
          isProcessing.value = false;

          voiceSocket.startAudio(rid, {
            sample_rate: 16000,
            channels: 1,
            encoding: 'pcm_s16le',
            vad_enabled: true,
            vad_silence_ms: 700,
          });
          setStatus('检测到语音，正在识别...', 'listening');
        }

        // 只有有 request_id 时才上传 chunk。
        if (currentRequestId.value) {
          voiceSocket.sendAudioChunkWsV1(currentRequestId.value, data, wsV1PreferBinary.value);
        }
      });

    } catch (e) {
      console.error(e);
      setStatus('无法启动录音', 'error');
      isRecording.value = false;
    }
  };

  /**
   * 停止录音
   */
  const stopRecording = () => {
    autoCaptureEnabled.value = false;
    isRecording.value = false;
    audioManager.stopRecording();
    if (currentRequestId.value) {
      voiceSocket.endAudio(currentRequestId.value);
      currentRequestId.value = null;
    } else {
      // legacy fallback
      voiceSocket.send({ type: 'stop' });
    }
    isProcessing.value = false;
    setStatus('已暂停自动聆听', 'success');
  };

  /**
   * 切换录音状态 (开始/停止)
   */
  const toggleRecording = () => {
    if (isRecording.value) {
      stopRecording();
    } else {
      void startRecording();
    }
  };

  /**
   * 计算一段 PCM16 音频的 RMS（用于语音起始检测）。
   */
  const calcRms = (pcm: Int16Array): number => {
    if (!pcm || pcm.length === 0) return 0;
    let sum = 0;
    for (let i = 0; i < pcm.length; i++) {
      const v = pcm[i];
      sum += v * v;
    }
    return Math.sqrt(sum / pcm.length);
  };

  return {
    // State
    isRecording,
    isProcessing,
    isSpeaking,
    isConnected,
    autoCaptureEnabled,
    statusText,
    statusType,
    currentLanguage,
    currentScenario,
    currentDialogue,
    
    // Actions
    init,
    toggleRecording,
    startCustomSession,
    stopSession
  };
});
