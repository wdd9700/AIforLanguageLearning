# 02 - 代码规范

> **开发方法论**: Agentic Engineering + BMAD-METHOD + SDD  
> **版本**: v1.0  
> **最后更新**: 2026-03-30

---

## 一、通用代码规范

### 1.1 命名规范

#### 1.1.1 Python 命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块/包 | 小写，下划线分隔 | `pronunciation_engine`, `assessment_service` |
| 类 | 大驼峰 | `PhonemeAnalyzer`, `AssessmentResult` |
| 函数/方法 | 小写，下划线分隔 | `analyze_phonemes()`, `calculate_score()` |
| 常量 | 大写，下划线分隔 | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` |
| 私有成员 | 单下划线前缀 | `_internal_cache`, `_validate_input()` |
| 变量 | 小写，下划线分隔 | `user_input`, `audio_buffer` |

#### 1.1.2 TypeScript/Vue 命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件 | 大驼峰，多单词 | `PhonemeFeedback.vue`, `AudioRecorder.vue` |
| 组合式函数 | use前缀，小驼峰 | `useAudioRecorder()`, `useAssessment()` |
| 类型定义 | 大驼峰，Type后缀 | `AssessmentResultType`, `UserProfileType` |
| 接口 | 大驼峰，I前缀可选 | `IAssessmentConfig` 或 `AssessmentConfig` |
| 枚举 | 大驼峰 | `AssessmentDimension`, `SuggestionType` |

### 1.2 代码格式

#### 1.2.1 Python (Black + isort)

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'
extend-exclude = '''
/(
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
```

#### 1.2.2 TypeScript/Vue (Prettier + ESLint)

```json
// .prettierrc
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "endOfLine": "lf"
}
```

### 1.3 文档字符串规范

#### 1.3.1 Python (Google Style)

```python
def analyze_phonemes(
    audio: np.ndarray,
    reference_text: str,
    sample_rate: int = 16000
) -> PhonemeResult:
    """Analyze phonemes in audio against reference text.
    
    This function performs phoneme-level alignment and scoring using
    Wav2Vec2 CTC decoding. It returns detailed per-phoneme scores
    and alignment information.
    
    Args:
        audio: Audio waveform as numpy array, shape (n_samples,)
        reference_text: Expected text transcription
        sample_rate: Audio sample rate in Hz, defaults to 16000
        
    Returns:
        PhonemeResult containing:
            - phonemes: List of phoneme segments with scores
            - overall_score: Aggregate pronunciation score (0-100)
            - alignment: Time-aligned phoneme boundaries
            
    Raises:
        ValueError: If audio is empty or sample_rate is invalid
        AudioProcessingError: If audio preprocessing fails
        
    Example:
        >>> audio = load_audio("sample.wav")
        >>> result = analyze_phonemes(audio, "Hello world")
        >>> print(f"Score: {result.overall_score}")
        Score: 85.5
    """
```

---

## 二、Python 后端规范

### 2.1 项目结构

```
backend_fastapi/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI应用入口
│   ├── core/                   # 核心配置
│   │   ├── config.py
│   │   ├── security.py
│   │   └── logging.py
│   ├── api/                    # API路由
│   │   ├── v1/
│   │   │   ├── pronunciation.py
│   │   │   ├── assessment.py
│   │   │   └── dialogue.py
│   │   └── deps.py
│   ├── models/                 # 数据模型
│   │   ├── schemas.py
│   │   └── database.py
│   ├── services/               # 业务逻辑
│   │   ├── pronunciation/
│   │   ├── assessment/
│   │   └── dialogue/
│   ├── agents/                 # AI Agent实现
│   │   ├── base.py
│   │   ├── pronunciation_agent.py
│   │   └── assessment_agent.py
│   ├── infrastructure/         # 基础设施
│   │   ├── cache.py
│   │   ├── database.py
│   │   └── message_queue.py
│   └── utils/                  # 工具函数
├── tests/
├── alembic/
├── pyproject.toml
└── Dockerfile
```

### 2.2 FastAPI 规范

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import AssessmentRequest, AssessmentResponse
from app.services.assessment import AssessmentService
from app.api.deps import get_current_user, get_assessment_service

router = APIRouter(prefix="/assessment", tags=["assessment"])

@router.post(
    "/pronunciation",
    response_model=AssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate pronunciation",
    responses={
        400: {"description": "Invalid audio format"},
        413: {"description": "Audio file too large"},
    }
)
async def evaluate_pronunciation(
    request: AssessmentRequest,
    current_user: User = Depends(get_current_user),
    service: AssessmentService = Depends(get_assessment_service)
) -> AssessmentResponse:
    """Evaluate pronunciation from audio data."""
    try:
        result = await service.assess_pronunciation(
            audio=request.audio,
            reference_text=request.reference_text,
            user_id=current_user.id
        )
        return AssessmentResponse.from_result(result)
    except AudioProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio processing failed: {str(e)}"
        )
```

### 2.3 Pydantic 模型规范

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AssessmentDimension(str, Enum):
    PRONUNCIATION = "pronunciation"
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    FLUENCY = "fluency"


class PhonemeScore(BaseModel):
    phoneme: str = Field(..., description="ARPAbet phoneme symbol")
    score: float = Field(..., ge=0, le=100)
    start_time: float = Field(..., ge=0)
    end_time: float = Field(..., ge=0)
    is_correct: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "phoneme": "HH",
                "score": 92.5,
                "start_time": 0.15,
                "end_time": 0.25,
                "is_correct": True
            }
        }


class AssessmentRequest(BaseModel):
    audio: bytes = Field(..., description="Audio data in WAV format")
    reference_text: str = Field(..., min_length=1, max_length=5000)
    language: str = Field(default="en-US", regex="^[a-z]{2}-[A-Z]{2}$")
    detailed: bool = Field(default=True)
    
    @validator('audio')
    def validate_audio_size(cls, v: bytes) -> bytes:
        max_size = 10 * 1024 * 1024
        if len(v) > max_size:
            raise ValueError(f"Audio size exceeds {max_size} bytes")
        return v
```

---

## 三、TypeScript/Vue 前端规范

### 3.1 项目结构

```
app/v5/
├── src/
│   ├── components/
│   │   ├── common/
│   │   ├── pronunciation/
│   │   ├── assessment/
│   │   └── dialogue/
│   ├── composables/
│   ├── stores/
│   ├── services/
│   ├── types/
│   ├── utils/
│   └── views/
├── tests/
├── vite.config.ts
└── package.json
```

### 3.2 Vue 3 + Composition API 规范

```vue
<template>
  <div class="phoneme-feedback">
    <PhonemeItem
      v-for="phoneme in phonemes"
      :key="phoneme.id"
      :phoneme="phoneme"
      :is-selected="selectedId === phoneme.id"
      @click="selectPhoneme(phoneme)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import type { PhonemeScore } from '@/types/pronunciation'

interface Props {
  phonemes: PhonemeScore[]
  autoSelectFirst?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  autoSelectFirst: false
})

const emit = defineEmits<{
  (e: 'select', phoneme: PhonemeScore): void
}>()

const selectedId = ref<string | null>(null)

const selectedPhoneme = computed(() => {
  if (!selectedId.value) return null
  return props.phonemes.find(p => p.id === selectedId.value) || null
})

function selectPhoneme(phoneme: PhonemeScore): void {
  selectedId.value = phoneme.id
  emit('select', phoneme)
}

onMounted(() => {
  if (props.autoSelectFirst && props.phonemes.length > 0) {
    selectPhoneme(props.phonemes[0])
  }
})
</script>
```

---

## 四、Git 提交规范

### 4.1 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 4.2 类型说明

| 类型 | 说明 |
|------|------|
| **feat** | 新功能 |
| **fix** | 修复bug |
| **docs** | 文档更新 |
| **style** | 代码格式调整 |
| **refactor** | 重构 |
| **perf** | 性能优化 |
| **test** | 测试相关 |
| **chore** | 构建/工具相关 |

### 4.3 示例

```
feat(pronunciation): add phoneme-level visualization

- Implement PhonemeFeedback component
- Add color coding for different score ranges

Closes #123
```

---

## 五、变更日志

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-03-30 | 初始版本 | GitHub Copilot |
