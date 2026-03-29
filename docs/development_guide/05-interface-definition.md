# 05 - 接口定义

> **开发方法论**: Agentic Engineering + BMAD-METHOD + SDD  
> **版本**: v1.0  
> **最后更新**: 2026-03-30

---

## 一、接口设计原则

### 1.1 REST API 设计规范

- **URL 命名**: 小写、复数、连字符分隔
- **HTTP 方法**: GET(查询)、POST(创建)、PUT(更新)、DELETE(删除)
- **状态码**: 使用标准 HTTP 状态码
- **版本控制**: URL 路径中包含版本号 `/api/v1/`

### 1.2 WebSocket 设计规范

- **命名空间**: 按功能模块划分
- **消息格式**: JSON，包含 `type` 和 `payload`
- **心跳机制**: 30 秒一次 ping/pong
- **重连策略**: 指数退避，最大重试 5 次

---

## 二、核心接口定义

### 2.1 认证接口

#### POST /api/v1/auth/login

**请求:**
```json
{
  "username": "string",
  "password": "string",
  "captcha": "string"
}
```

**响应:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### POST /api/v1/auth/refresh

**请求:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**响应:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 900
}
```

---

### 2.2 单词模块接口

#### 查词流程

```
用户输入查询词
        │
        ▼
┌─────────────────────────┐
│ 1. Elasticsearch检索    │
│    (模糊+语义搜索)       │
└──────────┬──────────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
   找到         未找到
     │           │
     ▼           ▼
┌─────────┐  ┌─────────────────┐
│ 返回词汇 │  │ 2. LLM介入生成   │
│ 信息     │  │ (Kimi API)      │
│          │  │                 │
│ 同时获取 │  │ 生成:           │
│ 关联词汇 │  │ - 音标          │
│ ↓        │  │ - 释义          │
│ ↓        │  │ - 例句          │
│ ↓        │  │ - 词性标签      │
└────┬─────┘  └────────┬────────┘
     │                 │
     └────────┬────────┘
              ▼
┌─────────────────────────┐
│ 3. 匹配关联词汇          │
│ (Neo4j知识图谱)          │
│                         │
│ • 近义词 (synonyms)      │
│ • 反义词 (antonyms)      │
│ • 同根词 (cognates)      │
│ • 形近词 (look-alikes)   │
│ • 音近词 (sound-alikes)  │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 4. 推荐复习              │
│ (基于用户画像)           │
│                         │
│ • 薄弱点相关词汇         │
│ • 关联词汇推荐           │
│ • 个性化学习计划         │
└─────────────────────────┘
```

#### GET /api/v1/words/search

**查询参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| q | string | 是 | 查询词 |
| fuzzy | boolean | 否 | 模糊搜索 |
| include_relations | boolean | 否 | 包含关联词汇 |
| limit | integer | 否 | 返回数量，默认 10 |

**响应 (ES找到):**
```json
{
  "source": "elasticsearch",
  "word": {
    "id": "word_001",
    "word": "pronunciation",
    "phonetic": "/prəˌnʌnsiˈeɪʃn/",
    "meanings": [...],
    "examples": [...],
    "tags": ["academic", "intermediate"],
    "difficulty": "B2"
  },
  "relations": {
    "synonyms": [
      {"word": "enunciation", "similarity": 0.92}
    ],
    "antonyms": [
      {"word": "mispronunciation", "similarity": 0.85}
    ],
    "cognates": [
      {"word": "pronounce", "type": "verb_form"},
      {"word": "pronounced", "type": "adjective_form"}
    ],
    "look_alikes": [
      {"word": "pronounciation", "note": "常见拼写错误"}
    ],
    "sound_alikes": [
      {"word": "pronounciation", "note": "发音相似但拼写错误"}
    ]
  },
  "recommendations": {
    "for_review": ["enunciation", "articulation"],
    "next_to_learn": ["intonation", "stress_pattern"]
  }
}
```

**响应 (ES未找到，LLM生成):**
```json
{
  "source": "llm_generated",
  "word": {
    "word": "newly_coined_word",
    "phonetic": "/ˈnjuːli kɔɪnd wɜːrd/",
    "meanings": [...],
    "examples": [...],
    "confidence": 0.85,
    "generated_at": "2026-03-30T10:00:00Z"
  },
  "relations": {
    "synonyms": [...],
    "cognates": [...]
  },
  "note": "该词汇由AI生成，建议人工核实"
}
```

#### GET /api/v1/words/{word_id}/relations

**响应:**
```json
{
  "word": "pronunciation",
  "relations": {
    "synonyms": {
      "description": "意义相近的词汇，可丰富表达",
      "items": [
        {"word": "enunciation", "similarity": 0.92, "context": "正式场合"},
        {"word": "articulation", "similarity": 0.88, "context": "发音清晰度"}
      ]
    },
    "antonyms": {
      "description": "意义相反的词汇，帮助理解对比",
      "items": [
        {"word": "mispronunciation", "similarity": 0.85}
      ]
    },
    "cognates": {
      "description": "同根词汇，帮助记忆词族",
      "items": [
        {"word": "pronounce", "type": "verb", "relation": "动词形式"},
        {"word": "pronounced", "type": "adjective", "relation": "形容词形式"},
        {"word": "pronounceable", "type": "adjective", "relation": "派生词"}
      ]
    },
    "look_alikes": {
      "description": "形近词汇，注意区分避免混淆",
      "items": [
        {"word": "pronounciation", "note": "常见拼写错误，多了一个'o'"},
        {"word": "pronunication", "note": "漏掉了's'"}
      ]
    },
    "sound_alikes": {
      "description": "音近词汇，听力辨识练习",
      "items": [
        {"word": "announcement", "note": "发音部分相似"}
      ]
    }
  }
}
```

#### POST /api/v1/words/generate

**请求:**
```json
{
  "topic": "business",
  "difficulty": "intermediate",
  "count": 20
}
```

**响应:**
```json
{
  "task_id": "gen_001",
  "status": "processing",
  "estimated_seconds": 30
}
```

---

### 2.3 作文模块接口

#### 作文批改流程

```
用户提交作文图片
        │
        ▼
┌─────────────────────────┐
│ 1. OCR文本提取          │
│    (PaddleOCR)          │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 2. 专业语料库检查        │
│    (LanguageTool API)   │
│                         │
│ • 拼写错误检测           │
│ • 基础语法检查           │
│ • 标点符号规范           │
│ • 常见搭配检查           │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 3. GEC语法纠错          │
│    (T5-GECToR)          │
│                         │
│ • 深层语法错误           │
│ • 句法结构问题           │
│ • 时态语态错误           │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 4. LLM综合分析          │
│    (本地qwen3.5-9B)     │
│                         │
│ 输入:                   │
│ • OCR文本               │
│ • 语料库检查结果        │
│ • GEC纠错结果           │
│ • 基础评分              │
│                         │
│ 输出:                   │
│ • 内容分析              │
│ • 结构评价              │
│ • 语言评价              │
│ • 综合建议              │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 5. 多维度评分            │
│    (算法聚合)            │
│                         │
│ 内容(30%) + 结构(25%)   │
│ + 语言(25%) + 语法(20%) │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 6. 结果聚合展示          │
│    (错误标注+改进建议    │
│     +范文对比+能力雷达)  │
└─────────────────────────┘
```

#### POST /api/v1/essays/submit

**请求 (multipart/form-data):**
| 字段 | 类型 | 说明 |
|------|------|------|
| image | file | 作文图片 |
| title | string | 作文标题 |
| user_id | string | 用户ID |

**响应:**
```json
{
  "essay_id": "essay_001",
  "status": "processing",
  "check_url": "/api/v1/essays/essay_001/status"
}
```

#### GET /api/v1/essays/{essay_id}/result

**响应:**
```json
{
  "essay_id": "essay_001",
  "status": "completed",
  "processing_pipeline": [
    "ocr_extraction",
    "corpus_check",
    "gec_correction",
    "llm_analysis"
  ],
  "scores": {
    "content": {
      "score": 8.5,
      "weight": 0.30,
      "breakdown": {
        "theme_relevance": 9.0,
        "depth": 8.0,
        "argumentation": 8.5
      }
    },
    "structure": {
      "score": 7.5,
      "weight": 0.25,
      "breakdown": {
        "organization": 8.0,
        "transitions": 7.0,
        "coherence": 7.5
      }
    },
    "language": {
      "score": 8.0,
      "weight": 0.25,
      "breakdown": {
        "vocabulary": 8.5,
        "variety": 7.5,
        "rhetoric": 8.0
      }
    },
    "grammar": {
      "score": 7.0,
      "weight": 0.20,
      "source": "gec_corpora_combined",
      "breakdown": {
        "error_density": 0.15,
        "spelling": 8.0,
        "punctuation": 7.5
      }
    },
    "overall": 7.75
  },
  "errors": [
    {
      "type": "grammar",
      "source": "gec_t5_gector",
      "position": { "start": 45, "end": 52 },
      "original": "He don't",
      "suggestion": "He doesn't",
      "explanation": "Third person singular requires 'does'",
      "severity": "medium",
      "category": "subject_verb_agreement"
    },
    {
      "type": "spelling",
      "source": "languagetool_api",
      "position": { "start": 120, "end": 128 },
      "original": "accomodate",
      "suggestion": "accommodate",
      "explanation": "Double 'c' and double 'm'",
      "severity": "low"
    }
  ],
  "corpus_references": [
    {
      "type": "grammar_rule",
      "source": "LanguageTool",
      "rule_id": "AGREEMENT_SENT_START",
      "description": "Subject-verb agreement"
    }
  ],
  "feedback": {
    "summary": "Overall good work with minor grammar issues...",
    "strengths": [
      "Clear thesis statement",
      "Good use of transition words"
    ],
    "weaknesses": [
      "Some subject-verb agreement errors",
      "Could use more complex sentence structures"
    ],
    "improvements": [
      "Practice subject-verb agreement rules",
      "Try using more subordinate clauses"
    ]
  },
  "model_references": [
    {
      "type": "example_sentence",
      "original": "He don't like apples.",
      "corrected": "He doesn't like apples.",
      "explanation": "Third person singular uses 'does'"
    }
  ]
}
```

---

### 2.4 对话模块接口

#### 场景扩写流程

```
用户输入场景描述
        │
        ▼
┌─────────────────────────┐
│ POST /api/v1/dialogue/  │
│    scenes/expand        │
│                         │
│ 请求:                   │
│ {                       │
│   "user_description":   │
│     "我想练习餐厅点餐",  │
│   "user_level": "B1",   │
│   "target_duration":    │
│     "10-15分钟"         │
│ }                       │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ Kimi API 思考模式扩写    │
│ (K2.5-thinking)         │
│                         │
│ Prompt: "作为场景设计    │
│ 专家，请将用户描述扩展   │
│ 为完整对话场景..."       │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 生成结构化场景配置       │
│ {                       │
│   "scene_name": "...",  │
│   "setting": {...},     │
│   "learning_objectives":│
│     [...],              │
│   "key_vocabulary":     │
│     [...],              │
│   "system_prompt":      │
│     "你是一位..."        │
│ }                       │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 存储为对话LLM的         │
│ System Prompt           │
│ (Qwen3.5-9B INT4)       │
└─────────────────────────┘
```

#### POST /api/v1/dialogue/scenes/expand

**请求:**
```json
{
  "user_description": "我想练习餐厅点餐",
  "user_level": "B1",
  "target_duration": "10-15分钟",
  "preferences": {
    "formality": "casual",
    "cuisine_type": "american"
  }
}
```

**响应:**
```json
{
  "scene_id": "scene_001",
  "scene_name": "美式休闲餐厅点餐",
  "setting": {
    "location": "美式休闲餐厅",
    "time": "晚餐时段",
    "roles": ["顾客(用户)", "服务员"],
    "atmosphere": "轻松友好"
  },
  "learning_objectives": [
    "掌握点餐常用表达",
    "学会询问推荐和特殊要求",
    "练习礼貌用语和支付方式表达"
  ],
  "key_vocabulary": [
    {"word": "appetizer", "phonetic": "/ˈæpɪtaɪzər/", "meaning": "开胃菜"},
    {"word": "entree", "phonetic": "/ˈɑːntreɪ/", "meaning": "主菜"}
  ],
  "system_prompt": "你是一位友好的餐厅服务员...",
  "opening_line": "Hi, welcome to our restaurant! ...",
  "estimated_duration": "10-15分钟",
  "difficulty_level": "intermediate"
}
```

#### WebSocket /ws/dialogue

**连接:**
```
/ws/dialogue?token={jwt_token}&scene_id=scene_001
```

**流程说明:**
1. 用户通过 `/scenes/expand` 创建场景
2. 服务端调用 Kimi API (思考模式) 扩写场景
3. 生成的 `system_prompt` 作为 Qwen3.5-9B 的 System Prompt
4. WebSocket 连接使用扩写后的场景配置

**客户端→服务端:**
```json
{
  "type": "audio_chunk",
  "payload": {
    "data": "base64_encoded_audio",
    "is_final": false
  }
}
```

```json
{
  "type": "text_message",
  "payload": {
    "text": "Hello, how are you?"
  }
}
```

**服务端→客户端:**
```json
{
  "type": "asr_partial",
  "payload": {
    "text": "Hello how",
    "is_final": false
  }
}
```

```json
{
  "type": "ai_response",
  "payload": {
    "text": "I'm doing well, thank you! How can I help you today?",
    "audio_url": "/audio/resp_001.mp3",
    "suggestions": ["Try saying: 'I'm fine, thanks'"]
  }
}
```

---

### 2.5 实时助教接口 **[最后开发，最亮点，最难]**

#### WebSocket /ws/assistant

**连接:**
```
/ws/assistant?token={jwt_token}&classroom_id=cls_001
```

**架构说明:**
- 运行位置: 仅教师端，学生端无感知
- AI服务: 统一使用 Kimi API (K2.5)，本地仅预处理
- 屏幕捕获: 720P下采样，保留鼠标轨迹(非ROI裁剪)
- 五级筛选: L0→L1→L2→L3→L4，节省97% Token

**客户端→服务端 (L0-L2 前端处理):**

```json
// L0: 输入事件捕获
{
  "type": "input_event",
  "payload": {
    "event_type": "keydown",
    "key": "PageDown",
    "timestamp": 1711800000000
  }
}
```

```json
// L1: 框选行为识别结果 (前端WebGL/ONNX)
{
  "type": "lasso_detected",
  "payload": {
    "region": { "x1": 100, "y1": 200, "x2": 400, "y2": 300 },
    "confidence": 0.92,
    "timestamp": 1711800000100,
    "screen_resolution": { "width": 1920, "height": 1080 }
  }
}
```

```json
// L2: 屏幕帧 (哈希去重后)
{
  "type": "screen_frame",
  "payload": {
    "image": "base64_encoded_jpeg_720p",
    "timestamp": 1711800000000,
    "resolution": { "width": 1280, "height": 720 },
    "hash": "a1b2c3d4",
    "has_mouse_trail": true
  }
}
```

```json
// 音频流 (ASR输入)
{
  "type": "audio_chunk",
  "payload": {
    "data": "base64_encoded_opus",
    "is_final": false,
    "timestamp": 1711800000200
  }
}
```

**服务端→客户端:**

```json
// ASR识别结果
{
  "type": "asr_result",
  "payload": {
    "text": "现在完成时的用法1是什么",
    "is_final": true,
    "confidence": 0.95,
    "detected_signals": ["explicit_wakeup"]
  }
}
```

```json
// 被动服务 (教师明确提问)
{
  "type": "on_demand_suggestion",
  "payload": {
    "id": "sugg_001",
    "trigger": "explicit_request",
    "content": "用法1表示过去动作对现在的影响，例如: I have lost my key.",
    "audio_data": "base64_encoded_audio",
    "context": {
      "lasso_region": { "x1": 100, "y1": 200, "x2": 400, "y2": 300 },
      "asr_text": "现在完成时的用法1是什么"
    }
  }
}
```

```json
// 主动服务 - 轻量提示 (不打断)
{
  "type": "proactive_hint",
  "payload": {
    "id": "hint_001",
    "trigger": "hesitation_detected",
    "icon": "💡",
    "preview": "例句提示",
    "position": "bottom-right",
    "opacity": 0.6,
    "click_to_expand": true,
    "ttl_seconds": 10
  }
}
```

```json
// 主动服务 - 主动辅助 (等待合适时机)
{
  "type": "proactive_assist",
  "payload": {
    "id": "assist_001",
    "trigger": "repetition_detected",
    "urgency": "medium",
    "content": "学生常混淆用法1和用法2，建议对比: I have lived here for 5 years (持续) vs I have lost my key (影响).",
    "audio_data": "base64_encoded_audio",
    "delivery_timing": "after_pause",
    "display_duration": 30
  }
}
```

```json
// 主动服务 - 重要提醒 (立即)
{
  "type": "proactive_alert",
  "payload": {
    "id": "alert_001",
    "trigger": "correction_detected",
    "urgency": "high",
    "content": "确认: 正确表达是 'He has gone' 而非 'He has been'.",
    "audio_data": "base64_encoded_audio",
    "visual_indicator": {
      "type": "banner",
      "color": "yellow"
    }
  }
}
```

---

## 三、数据模型定义

### 3.1 通用模型

```typescript
// types/api.ts

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  timestamp: number;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

interface ErrorResponse {
  code: string;
  message: string;
  details?: Record<string, any>;
  path: string;
  timestamp: number;
}
```

### 3.2 业务模型

```typescript
// types/pronunciation.ts

interface PhonemeScore {
  id: string;
  phoneme: string;
  score: number;
  start_time: number;
  end_time: number;
  is_correct: boolean;
  confidence: number;
}

interface ProsodyFeatures {
  pitch_contour: number[];
  intensity_envelope: number[];
  duration_pattern: number[];
  speaking_rate: number;
}

interface PronunciationResult {
  id: string;
  overall_score: number;
  phonemes: PhonemeScore[];
  prosody?: ProsodyFeatures;
  feedback: string;
  created_at: string;
}
```

```typescript
// types/assessment.ts

enum AssessmentDimension {
  PRONUNCIATION = 'pronunciation',
  GRAMMAR = 'grammar',
  VOCABULARY = 'vocabulary',
  FLUENCY = 'fluency',
  COHERENCE = 'coherence'
}

interface DimensionScore {
  dimension: AssessmentDimension;
  score: number;
  weight: number;
  feedback: string;
}

interface AssessmentResult {
  id: string;
  overall_score: number;
  dimension_scores: DimensionScore[];
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  created_at: string;
}
```

---

## 四、错误码定义

### 4.1 HTTP 状态码

| 状态码 | 含义 | 场景 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突 |
| 413 | Payload Too Large | 请求体过大 |
| 422 | Unprocessable Entity | 验证错误 |
| 429 | Too Many Requests | 限流 |
| 500 | Internal Server Error | 服务器错误 |
| 503 | Service Unavailable | 服务不可用 |

### 4.2 业务错误码

| 错误码 | 说明 | HTTP 状态 |
|--------|------|-----------|
| AUTH_001 | Token 过期 | 401 |
| AUTH_002 | Token 无效 | 401 |
| AUTH_003 | 密码错误 | 401 |
| USER_001 | 用户不存在 | 404 |
| USER_002 | 用户已存在 | 409 |
| WORD_001 | 单词不存在 | 404 |
| ESSAY_001 | 作文处理中 | 202 |
| ESSAY_002 | 作文处理失败 | 500 |
| AUDIO_001 | 音频格式错误 | 400 |
| AUDIO_002 | 音频过大 | 413 |
| MODEL_001 | 模型推理超时 | 504 |
| MODEL_002 | 模型服务不可用 | 503 |

---

## 五、接口版本策略

### 5.1 版本控制

| 版本 | 状态 | 支持期限 |
|------|------|----------|
| v1 | Current | 2027-03-30 |
| v2 | Planned | - |

### 5.2 兼容性规则

- 新增字段: 向后兼容
- 删除字段: 需要新版本
- 修改字段类型: 需要新版本
- 修改 URL: 需要新版本

---

## 六、变更日志

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-03-30 | 初始版本 | GitHub Copilot |
