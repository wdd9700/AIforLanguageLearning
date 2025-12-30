/**
 * @fileoverview 环境配置模块 (Environment Configuration)
 * @description
 * 该文件统一管理后端服务的所有配置项，负责从 .env 文件加载环境变量，并提供类型安全的配置对象供其他模块使用。
 * 
 * 主要功能：
 * 1. 基础配置：服务器端口、运行环境 (Dev/Prod)、CORS 策略
 * 2. 数据库配置：SQLite 数据库文件路径
 * 3. 外部服务配置：
 *    - LLM: LM Studio 端点、模型路由策略 (Conversation/OCR/Analysis)、Prompt 模板
 *    - OCR: PaddleOCR 脚本路径、GPU 开关
 *    - ASR: Faster-Whisper 模型大小、计算精度、设备选择
 *    - TTS: XTTS v2 脚本路径、参考音频路径
 * 4. 安全配置：JWT 密钥、过期时间、管理员初始凭据
 * 5. 运行时配置：Python 解释器路径、日志级别、会话超时设置
 * 
 * 设计原则：
 * - 优先使用环境变量 (process.env)
 * - 提供合理的默认值，确保开箱即用
 * - 集中管理路径和常量，避免硬编码
 * 
 * 待改进项：
 * - [ ] 引入 Zod 或 Joi 进行严格的环境变量 Schema 验证
 * - [ ] 支持从远程配置中心 (如 Consul/Etcd) 加载配置
 * - [ ] 区分 Secret 和 Config，避免敏感信息明文存储
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import dotenv from 'dotenv';
import path from 'path';

// 加载 .env 文件
dotenv.config();

export const config = {
  // 服务器配置
  // 监听端口（优先使用 AIFL_NODE_PORT；否则兼容 PORT；最终回退 3006）
  port: parseInt(process.env.AIFL_NODE_PORT || process.env.PORT || '3006', 10),
  // 运行环境：development, production, test
  env: process.env.NODE_ENV || 'development',
  // CORS 配置（跨域资源共享）
  cors: {
    // 允许的来源列表，支持逗号分隔。默认为 '*' (允许所有)
    origin: process.env.CORS_ORIGIN ? process.env.CORS_ORIGIN.split(',').map(s => s.trim()) : '*'
  },
  
  // 数据库配置
  database: {
    // SQLite 数据库文件路径
    path: process.env.DB_PATH || path.join(__dirname, '../../data/app.db'),
  },

  // Python 环境配置
  // 用于执行 Python 脚本（ASR, TTS, OCR 等服务）
  // 建议在 .env 中配置 PYTHON_PATH 以指向正确的虚拟环境或解释器
  pythonPath: process.env.PYTHON_PATH || 'C:/Python314/python.exe', 
  
  // JWT (JSON Web Token) 配置
  // 用于用户认证和授权
  jwt: {
    // 签名密钥，生产环境务必修改
    secret: process.env.JWT_SECRET || 'your-super-secret-key-change-this-in-production',
    // Access Token 过期时间
    expiresIn: process.env.JWT_EXPIRES_IN || '7d',
    // Refresh Token 过期时间
    refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '30d',
  },
  
  // 管理员初始认证配置
  // 用于系统初始化或紧急访问
  admin: {
    user: process.env.ADMIN_USER || 'admin',
    password: process.env.ADMIN_PASSWORD || 'admin',
  },

  // 外部服务配置
  services: {
    // LLM 服务 (目前对接 LM Studio)
    // 支持多模型智能路由，根据任务类型选择不同的模型
    llm: {
      // LM Studio API 端点
      endpoint: process.env.LLM_ENDPOINT || 'http://localhost:1234/v1/chat/completions',
      // 请求超时时间 (毫秒)，大模型生成较慢，需设置较长时间
      timeout: 90000, 
      // 最大重试次数
      maxRetries: 3,
      // LMS 命令行工具名称 (用于模型加载/卸载)
      lmsCommand: 'lms',
      
      // 任务驱动的模型选择策略
      // key: 任务类型, value: 模型标识符 (需与 LM Studio 中加载的模型一致)
      models: {
        // 对话场景：通用能力较强的模型 (如 Qwen3 VL 8B)
        conversation: process.env.LLM_MODEL_CONVERSATION || 'qwen/qwen3-vl-8b',
        
        // OCR/词汇查询：具备视觉能力或强语言理解的模型
        vocabulary: process.env.LLM_MODEL_VOCABULARY || 'qwen/qwen3-vl-8b',
        ocr: process.env.LLM_MODEL_OCR || 'qwen/qwen3-vl-8b',
        
        // 教学分析：具备逻辑推理能力的模型 (如 Qwen3 4B Thinking)
        analysis: process.env.LLM_MODEL_ANALYSIS || 'qwen/qwen3-4b-thinking-2507',
        
        // 提示词扩写：具备逻辑推理能力的模型
        prompt_expansion: process.env.LLM_MODEL_PROMPT_EXPANSION || 'qwen/qwen3-4b-thinking-2507',

        // 意图识别：使用对话模型即可，速度较快
        router: process.env.LLM_MODEL_ROUTER || 'qwen/qwen3-vl-8b',

        // 作文批改：语言能力强的模型
        essay_correction: process.env.LLM_MODEL_ESSAY || 'qwen/qwen3-vl-8b',
      },

      // 模型加载参数配置 (Model Loading Configuration)
      // 定义每个模型加载时的具体参数，如 GPU 层数、上下文长度等
      loadConfig: {
        'qwen/qwen3-vl-8b': {
          gpu: 0.5, // Changed from gpu_offload_ratio to match CLI flag --gpu
          context_length: 8192,
        },
        'qwen/qwen3-4b-thinking-2507': {
          gpu: 0.5,
          context_length: 12288,
        }
      },
      
      // 系统提示词 (System Prompts) 配置
      // 定义了 AI 在不同任务中的角色和行为规范
      prompts: {
        vocabulary: process.env.PROMPT_VOCABULARY || `请以专业、清晰的文本形式输出以下内容。用户将提供一个英语单词（例如：analyze）。输出必须严格遵循以下结构，无任何emoji、列表符号（•/••）或冗余说明：

单词：[用户输入的单词]
词性：[符号]（中文解释）
（例：vt.（及物动词） | vi.（不及物动词） | n. [C]（可数名词） | n. [U]（不可数名词） | adj.（形容词） | adv.（副词））
（动词需包含过去式/分词读音：例：vt.（及物动词）（过去式：/əˈnælɪzɪd/，分词：/əˈnælɪzɪd/））
释义：
[最常用释义]：[例句]
[次常用释义]：[例句]
（按实际使用频率从高到低排序，每个释义仅1句例句，例句≤20词）
词源：[词根]（[来源语言]，[基本含义]）
同根词：
[词1]（[词性]）：[含义]；[区分说明]
[词2]（[词性]）：[含义]；[区分说明]
（仅列出非同义词，词性相同者需提供区分说明）
词缀：
前缀：[前缀]（[含义]）
后缀：[后缀]（[含义]）
同义词：
[词1]（[音标]）：[含义]；[与原词区分说明]
[词2]（[音标]）：[含义]；[与原词区分说明]
介词短语：
[短语1]：[含义]；[例句]；[辨析说明]
[短语2]：[含义]；[例句]；[辨析说明]
关键规则（模型必须严格遵守）：

信息优先级：词性 → 释义 → 词源 → 同根词 → 词缀 → 同义词 → 介词短语（用户3秒内可抓取核心信息）
语言规范：
词性用标准符号（如vt.、n. [C]）后紧跟中文解释（例：vt.（及物动词））
例句必须自然、简短（≤20词），无口语化表达
信息不适用时（如无同根词）跳过该部分，不添加“无”等说明
词源/同根词/辨析说明需精准区分（例：analysis (n.)：分解过程；侧重结果，analyze侧重动作）
深度优化：
释义按实际使用频率排序（非主观）
同根词严格标注非同义关系（例：analysis (n.) vs analyze (v.)）
介词短语提供可记忆的辨析点（例：analyze with data（强调工具））
零冗余：
禁止使用任何emoji、列表符号（•/••）、缩进或额外空行
每部分用短句描述（≤15词），避免技术术语堆砌`,
        essay: process.env.PROMPT_ESSAY || "You are an English teacher. Correct the following essay and provide feedback on grammar, vocabulary, and structure. Output a JSON object with keys: 'correction' (string), 'scores' (object with vocabulary, grammar, fluency, structure, other, total), and 'feedback' (string).",
        dialogue: process.env.PROMPT_DIALOGUE || "You are a helpful language learning partner. Engage in a conversation with the user, correcting their mistakes gently.",
        analysis: process.env.PROMPT_ANALYSIS || "You are a learning analyst. Analyze the user's learning data and provide insights on their progress and areas for improvement.",
        scenario_expansion: process.env.PROMPT_SCENARIO_EXPANSION || "You are an expert scenario designer for language learning. Your task is to take a short scenario description and expand it into a detailed system prompt for a role-playing AI. The system prompt should define the AI's role, the setting, the user's role, and the learning objectives. Output ONLY the system prompt.",
        // 预定义场景提示词
        scenarios: {
            daily: "You are a friendly neighbor. Chat about daily life, weather, and hobbies. Keep it casual and simple.",
            travel: "You are a travel guide or a fellow traveler. Discuss travel plans, directions, hotels, and sightseeing.",
            business: "You are a business professional. Discuss meetings, projects, negotiations, and workplace etiquette. Use formal language.",
            academic: "You are a professor or student. Discuss academic topics, research, and studies. Use academic vocabulary."
        }
      }
    },
    
    // OCR 服务 (PaddleOCR)
    // 用于图片文字识别
    ocr: {
      enabled: true,
      useGpu: true,
      pythonPath: process.env.OCR_PYTHON_PATH || 'C:/Users/74090/Miniconda3/py313/envs/ocr/python.exe',
      // PaddleOCR Python 包装脚本路径
      scriptPath: path.join(__dirname, '../../scripts/paddleocr_v3_wrapper.py'),
      // 默认识别语言
      langs: 'ch',
      timeout: 60000,
    },
    
    // ASR 服务 (Faster-Whisper)
    // 用于语音转文字
    asr: {
      modelSize: process.env.ASR_MODEL_SIZE || 'medium',
      device: process.env.ASR_DEVICE || 'cuda',
      computeType: process.env.ASR_COMPUTE_TYPE || 'int8',
      pythonPath: process.env.ASR_PYTHON_PATH || 'C:/Users/74090/Miniconda3/py313/envs/asr/python.exe',
      // Faster-Whisper Python 包装脚本路径
      scriptPath: path.join(__dirname, '../../scripts/faster_whisper_wrapper.py'),
      cpuThreads: 4,
      timeout: 120000 // Increased timeout for large audio files
    },
    
    // TTS 服务 (XTTS v2)
    // 用于文字转语音
    tts: {
      enabled: true,
      device: 'cuda',
      pythonPath: process.env.TTS_PYTHON_PATH || 'C:/Users/74090/Miniconda3/envs/torchnb311/python.exe',
      // XTTS Python 包装脚本路径
      scriptPath: path.join(__dirname, '../../scripts/xtts_wrapper.py'),
      // 声音克隆用的参考音频路径
      promptAudioPath: process.env.TTS_PROMPT_AUDIO_PATH || path.join(__dirname, '../../../testresources/TTSpromptAudio.wav'),
      timeout: 30000,
      env: {}
    },
  },
  
  // 会话管理配置
  session: {
    timeout: 30 * 60 * 1000, // 会话超时时间：30 分钟
    heartbeatInterval: 30000, // 心跳检测间隔：30 秒
  },
  
  // 日志配置
  log: {
    level: process.env.LOG_LEVEL || 'info', // 日志级别：debug, info, warn, error
    file: process.env.LOG_FILE || path.join(__dirname, '../../logs/app.log'), // 日志文件路径
  },

  // 自检与测试配置
  // 用于系统启动时的健康检查
  test: {
    ocrImage: path.join(__dirname, '../../../testresources/OCRtest.png'), // OCR 测试图片
    ttsText: 'Testing audio generation loop.', // TTS 测试文本
    llmPrompt: 'Please reply with exactly: test successfully', // LLM 测试提示词
    llmExpectedResponse: 'test successfully' // LLM 预期响应
  }
};

