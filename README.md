# 🤖 AI for Foreign Language Learning
### 全栈式本地化外语学习 AI 助手

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Vue](https://img.shields.io/badge/Vue.js-3.x-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-teal)
![LLM](https://img.shields.io/badge/AI-Local%20LLM-orange)

> **AI for Foreign Language Learning** 是一个集成了词汇深度解析、作文智能批改与口语对话陪练的现代化外语学习平台。项目采用前后端分离架构，完全基于本地 LLM（如 LM Studio）运行，确保数据隐私与零延迟交互体验。

---

## ✨ 核心功能与工作流 (Core Features)

### 1. 📖 智能词汇深度解析 (Deep Vocabulary Analysis)
不再局限于简单的字典释义。AI 助手会根据用户查询的单词，生成包含多义项、场景例句及中文对照的结构化知识卡片。

- **工作流程**:
  1. **User Query**: 用户输入单词（如 "set"）。
  2. **LLM Inference**: 后端构建 Prompt，要求 LLM 输出包含 `definitions`（释义/例句/翻译）的严格 JSON 格式。
  3. **Robust Parsing**: 后端通过自动修复机制（Json Repair、Double-Decode）处理 LLM 可能产生的脏数据。
  4. **Visualization**: 前端渲染多义项卡片，展示丰富的例句与翻译。
  
### 2. 📝 作文智能批改 (Essay Correction & Scoring)
提供雅思/托福级别的写作评分与润色建议。

- **工作流程**:
  1. **Input**: 支持纯文本输入或图片粘贴（未来集成 OCR）。
  2. **AI Grading**: 系统调用 LLM 从 6 个维度（词汇、语法、逻辑、流畅度、内容、结构）进行 0-100 评分。
  3. **Feedback**: 生成综合点评、错误纠正（Errors）、改进建议（Suggestions）及全文润色版本。
  4. **Analytics**: 前端通过 **ECharts 雷达图** 直观展示各项能力分布。

### 3. 🎙️ 实时口语对话 (Voice & Diagnosis)
模拟真人外教的实时语音交互环境。

- **工作流程**:
  1. **Streaming**: 前端通过 WebSocket 实时传输音频流。
  2. **VAD & ASR**: 后端集成 Voice Activity Detection 检测停顿，使用 Faster-Whisper 进行语音转文字。
  3. **Interaction**: 将识别文本送入 LLM 对话上下文。
  4. **TTS**: 文本转语音（支持 XTTS 或标准 TTS）返回前端播放。

---

## 🛠️ 技术栈 (Tech Stack)

### 🖥️ 前端 (Frontend) - `app/v5`
- **Framework**: [Vue 3](https://vuejs.org/) (Composition API) + [Vite](https://vitejs.dev/)
- **State Management**: [Pinia](https://pinia.vuejs.org/)
- **UI & Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Visualization**: [ECharts](https://echarts.apache.org/) (用于能力雷达图)
- **Network**: Axios + WebSocket (原生)

### ⚡ 后端 (Backend) - `backend_fastapi`
- **Core Framework**: [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn
- **Language**: Python 3.10+ (Type Hinting 覆盖)
- **Data & ORM**: [SQLModel](https://sqlmodel.tiangolo.com/) (SQLite)
- **AI Integration**:
  - OpenAI-Compatible Generic Client (适配 LM Studio / Ollama / vLLM)
  - Jinja2 Prompt Templates (结构化 Prompt 管理)
  - Robust JSON Parser (自研解析器，处理 LLM 非标输出)
- **DevOps**: PowerShell Automation Scripts

---

## 🚀 快速开始 (Getting Started)

### 环境要求
- Windows 10/11 (推荐开发环境)
- Python 3.10+
- Node.js 16+ & npm
- [LM Studio](https://lmstudio.ai/) (或其他兼容 OpenAI 接口的本地模型服务)

### 第一步：启动 LM Studio
1. 下载并加载一个语言模型（推荐 Qwen2.5-7B-Instruct 或 Llama-3-8B）。
2. 开启 Local Server，确保端口为 `1234`（默认）或在配置中修改。

### 第二步：一键启动项目
我们提供了自动化的 PowerShell 脚本用于环境检查与服务启动。

```powershell
# 在项目根目录下运行
./scripts/start.ps1
```

**脚本将执行以下操作**：
- 🟢 检查 Python 虚拟环境与依赖。
- 🟢 自动迁移前端/后端配置文件（端口 `8012`）。
- 🚀 启动 FastAPI 后端服务。
- 🚀 启动 Vue 前端开发服务器。

---

## ⚙️ 配置说明 (Configuration)

| 配置文件路径 | 说明 |
| :--- | :--- |
| `backend_fastapi/.env` | 后端环境变量（LLM 地址、端口、数据库路径等）。 |
| `backend_fastapi/app/settings.py` | 后端核心配置逻辑 (Pydantic Settings)。 |
| `app/v5/src/services/config.ts` | 前端 API 端点配置 (默认自动适配 localhost:8012)。 |

---

## 🤝 贡献 (Contributing)
欢迎提交 Issue 或 Pull Request！

---
*Created with ❤️ by wdd9700*
