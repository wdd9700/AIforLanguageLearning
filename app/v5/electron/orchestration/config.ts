/**
 * @fileoverview 默认编排器配置 (Default Orchestrator Configuration)
 * @description
 * 该文件定义了服务编排系统的默认配置，包括服务定义、路由规则、管道配置等。
 * 
 * 配置内容包括：
 * 1. 服务定义 (Services)：
 *    - OCR (Surya)
 *    - ASR (Whisper)
 *    - TTS (Cosy)
 *    - LLM (LM Studio)
 * 
 * 2. 路由规则 (Routes)：
 *    - 定义了不同主题 (svc/ocr, svc/asr 等) 到服务的映射
 *    - 包含词汇查询 (query/vocabulary) 的特殊路由
 * 
 * 3. 管道定义 (Pipelines)：
 *    - 翻译管道 (translate_pipeline)
 *    - 语音理解管道 (speech_to_understanding)
 * 
 * 4. 预热与缓存 (Warmup & Cache)：
 *    - 定义了模型预热策略和缓存参数
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { OrchestratorConfig } from '../orchestration/types.js';

export const defaultOrchestratorConfig: OrchestratorConfig = {
  services: {
    // OCR 服务（Surya）- 使用 HTTP 接口
    ocr: {
      name: 'ocr',
      type: 'http',
      endpoint: 'http://localhost:8011',
      healthCheck: '/health',
      healthCheckInterval: 30000,
      priority: 90,
      autoRestartCount: 3,
      autoRestartDelay: 2000,
    },

    // ASR 服务（Whisper）- 使用 HTTP 接口
    asr: {
      name: 'asr',
      type: 'http',
      endpoint: 'http://localhost:8001',
      healthCheck: '/health',
      healthCheckInterval: 30000,
      priority: 80,
      autoRestartCount: 3,
      autoRestartDelay: 2000,
    },

    // TTS 服务（Cosy）- 使用 HTTP 接口
    tts: {
      name: 'tts',
      type: 'http',
      endpoint: 'http://localhost:8002',
      healthCheck: '/health',
      healthCheckInterval: 30000,
      priority: 70,
      autoRestartCount: 3,
      autoRestartDelay: 2000,
    },

    // LLM 服务（LM Studio）- 使用 HTTP 接口
    llm: {
      name: 'llm',
      type: 'http',
      endpoint: 'http://localhost:1234',
      healthCheck: '/health',
      healthCheckInterval: 30000,
      priority: 85,
      autoRestartCount: 3,
      autoRestartDelay: 2000,
      options: {
        modelName: 'qwen3-vl-8b-instruct'
      }
    },
  },

  // 消息路由规则
  routes: [
    // OCR 请求路由
    {
      pattern: 'svc/ocr',
      serviceName: 'ocr',
      priority: 100,
      timeout: 60000,
      isStream: false,
    },

    // ASR 请求路由
    {
      pattern: 'svc/asr',
      serviceName: 'asr',
      priority: 100,
      timeout: 120000, // 语音处理可能更耗时
      isStream: false,
    },

    // TTS 请求路由
    {
      pattern: 'svc/tts',
      serviceName: 'tts',
      priority: 100,
      timeout: 30000,
      isStream: false,
    },

    // LLM 推理路由
    {
      pattern: 'svc/llm',
      serviceName: 'llm',
      priority: 100,
      timeout: 180000, // 推理可能较耗时
      isStream: false,
    },
    
    // 词汇查询路由 (映射到 LLM)
    {
      pattern: 'query/vocabulary',
      serviceName: 'llm',
      priority: 100,
      timeout: 60000,
      isStream: false,
    },

    // 复杂管道路由
    {
      pattern: 'svc/translate',
      serviceName: 'translate_pipeline',
      priority: 80,
      timeout: 300000,
      isStream: false,
    },

    // 回退路由（用于测试）
    {
      pattern: 'svc/*',
      serviceName: 'echo',
      priority: 10,
      timeout: 5000,
      isStream: false,
    },
  ],

  // 管道定义（复杂多步处理）
  pipelines: {
    // OCR + 翻译管道
    translate_pipeline: {
      name: 'translate_pipeline',
      steps: [
        {
          name: 'ocr_step',
          serviceName: 'ocr',
          timeout: 60000,
          retries: 1,
          continueOnError: false,
        },
        {
          name: 'translate_step',
          serviceName: 'llm',
          timeout: 120000,
          retries: 1,
          continueOnError: false,
        },
      ],
      parallel: false,
      timeout: 300000,
    },

    // 语音到文本再到语义理解
    speech_to_understanding: {
      name: 'speech_to_understanding',
      steps: [
        {
          name: 'asr_step',
          serviceName: 'asr',
          timeout: 120000,
        },
        {
          name: 'llm_step',
          serviceName: 'llm',
          timeout: 60000,
        },
      ],
      parallel: false,
      timeout: 240000,
    },
  },

  // 模型预热配置
  warmupConfigs: [
    {
      modelId: 'default-ocr',
      serviceName: 'ocr',
      input: { image: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==' },
      priority: 100,
      timeout: 30000,
    },
    {
      modelId: 'default-llm',
      serviceName: 'llm',
      input: { prompt: 'Hello' },
      priority: 90,
      timeout: 60000,
    },
  ],

  // 缓存配置
  cacheConfig: {
    enabled: true,
    ttl: 300000, // 5 分钟
    maxSize: 100,
  },

  // 全局配置
  globalTimeout: 300000, // 5 分钟
  healthCheckInterval: 30000,
  maxConcurrency: 10,
  enableTracing: true,
  logLevel: 'info',
};

/**
 * 创建用于测试的最小配置
 */
export const minimalOrchestratorConfig: OrchestratorConfig = {
  services: {
    // 简单的 echo 服务用于测试
    echo: {
      name: 'echo',
      type: 'http',
      endpoint: 'http://localhost:9999', // 测试端点
      priority: 50,
    },
  },

  routes: [
    {
      pattern: 'test/echo',
      serviceName: 'echo',
      priority: 100,
      timeout: 5000,
    },
  ],

  globalTimeout: 30000,
  logLevel: 'debug',
};
