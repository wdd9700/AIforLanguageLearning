# 算力受限环境（12GB VRAM）画面变化感知与理解技术方案调研

## 目录
1. [技术方向调研](#1-技术方向调研)
2. [边云协同架构设计](#2-边云协同架构设计)
3. [12GB VRAM 可行方案](#3-12gb-vram-可行方案)
4. [实际产品/开源项目参考](#4-实际产品开源项目参考)
5. [技术对比表](#5-技术对比表)
6. [推荐配置与代码示例](#6-推荐配置与代码示例)

---

## 1. 技术方向调研

### 1.1 画面变化检测方法

#### 1.1.1 光流法 (Optical Flow)

光流法通过分析连续帧之间的像素运动来检测画面变化，是计算视觉中的经典方法。

**稀疏光流 (Sparse Optical Flow)**
- **算法**: Lucas-Kanade (LK) 算法
- **计算开销**: 极低 (~1-5ms/帧 @ 1080p)
- **显存需求**: < 100MB
- **适用场景**: 检测显著运动区域、跟踪特征点
- **优势**: 计算极快，适合实时应用
- **劣势**: 对纹理缺失区域敏感，无法检测静态变化

**稠密光流 (Dense Optical Flow)**
- **算法**: Farneback、RAFT、PWC-Net
- **计算开销**: 
  - Farneback: ~10-30ms/帧 (CPU)
  - RAFT: ~50-100ms/帧 (GPU)
  - PWC-Net: ~30-50ms/帧 (GPU)
- **显存需求**: 200MB - 1GB
- **适用场景**: 全画面运动分析、场景变化检测
- **优势**: 提供像素级运动信息
- **劣势**: 计算成本较高，对光照变化敏感

**实现建议**:
```python
# OpenCV Lucas-Kanade 稀疏光流
import cv2
import numpy as np

lk_params = dict(
    winSize=(15, 15),
    maxLevel=2,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
)

# 检测 Shi-Tomasi 角点作为特征点
feature_params = dict(
    maxCorners=100,
    qualityLevel=0.3,
    minDistance=7,
    blockSize=7
)
```

#### 1.1.2 YOLO/目标检测

轻量级目标检测模型适合边缘设备部署，可用于检测画面中的关键元素变化。

**轻量模型对比**:

| 模型 | 参数量 | 推理时间 (GPU) | mAP@50 | 显存需求 |
|------|--------|----------------|--------|----------|
| YOLOv8n | 3.2M | ~2ms | 52.6 | ~300MB |
| YOLOv8s | 11.2M | ~3ms | 61.8 | ~500MB |
| YOLO-Nano | 1.5M | ~1.5ms | 45.2 | ~200MB |
| YOLO-Fastest | 0.35M | ~1ms | 38.5 | ~150MB |
| YOLO11n | 2.6M | ~1.8ms | 54.7 | ~280MB |
| MobileNet-SSD | 5.8M | ~5ms | 48.2 | ~400MB |

**教育场景专用检测**:
- **课件内容检测**: 检测 PPT/白板/屏幕区域
- **人物检测**: 检测教师/学生位置和动作
- **手势检测**: 检测指向、书写等教学手势

**实现建议**:
```python
from ultralytics import YOLO

# 边缘部署推荐模型
model = YOLO('yolov8n.pt')  # 或 yolo11n.pt

# INT8 量化推理
model.export(format='engine', int8=True)  # TensorRT INT8
```

#### 1.1.3 OCR 变化检测

针对教育课件场景，OCR 变化检测是识别文本内容变化的有效方法。

**技术栈**:
- **文本检测**: DBNet、PSENet、YOLO-Text
- **文本识别**: CRNN、SVTR、PARSeq
- **变化检测**: 文本区域对比 + 编辑距离算法

**轻量 OCR 方案**:

| 方案 | 检测模型 | 识别模型 | 总显存 | 速度 (1080p) |
|------|----------|----------|--------|--------------|
| PaddleOCR 轻量 | DBNet | SVTR_LCNet | ~500MB | ~100ms |
| EasyOCR | CRAFT | CRNN | ~800MB | ~150ms |
| RapidOCR | ch_PP-OCRv4 | ch_PP-OCRv4 | ~400MB | ~80ms |
| mmOCR | DBNet | SAR | ~600MB | ~120ms |

**变化检测策略**:
1. **区域变化检测**: 对比连续帧的文本区域位置变化
2. **内容变化检测**: 提取文本后计算编辑距离
3. **结构化变化**: 检测表格、列表、公式的结构变化

#### 1.1.4 VLM 轻量版

在 12GB VRAM 限制下，以下多模态模型可以运行：

**推荐模型 (batch=1)**:

| 模型 | 参数量 | FP16 显存 | INT4 显存 | 特点 |
|------|--------|-----------|-----------|------|
| MiniCPM-V 2.6 | 8B | ~18GB | ~6GB | 端侧最强，支持 OCR |
| MiniCPM-V 4.0 | 4B | ~10GB | ~4GB | 推荐首选，性能优秀 |
| Qwen2-VL-2B | 2B | ~5GB | ~2.5GB | 超轻量，基础理解 |
| Qwen2-VL-7B | 7B | ~16GB | ~6GB | 量化后可运行 |
| Qwen2.5-VL-3B | 3B | ~7GB | ~3GB | 新一代，性能提升 |
| LLaVA-Phi-3 | 3.8B | ~8GB | ~3.5GB | 微软出品，推理强 |
| LLaVA-v1.5-7B | 7B | ~16GB | ~6GB | 社区活跃 |
| InternVL2-4B | 4B | ~9GB | ~4GB | 中文优化 |
| Phi-3-Vision | 4.2B | ~9GB | ~4GB | 微软 SLM |

**量化方案对比**:

| 量化方法 | 精度损失 | 速度提升 | 显存节省 | 适用场景 |
|----------|----------|----------|----------|----------|
| AWQ | 低 | 1.5x | 60% | 推荐首选 |
| GPTQ | 低 | 1.3x | 60% | 通用量化 |
| bitsandbytes | 中 | 1.2x | 50% | 快速部署 |
| SmoothQuant | 低 | 1.4x | 55% | INT8 推理 |
| torchao INT4 | 中 | 1.6x | 70% | 极限压缩 |

**MiniCPM-V 4.0 部署示例**:
```python
import torch
from transformers import AutoModel, AutoTokenizer

model = AutoModel.from_pretrained(
    'openbmb/MiniCPM-V-4.0',
    trust_remote_code=True,
    torch_dtype=torch.float16
).cuda()

tokenizer = AutoTokenizer.from_pretrained(
    'openbmb/MiniCPM-V-4.0',
    trust_remote_code=True
)

# INT4 量化版本
from transformers import BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
)

model_int4 = AutoModel.from_pretrained(
    'openbmb/MiniCPM-V-4.0',
    trust_remote_code=True,
    quantization_config=quantization_config,
    device_map='auto'
)
```

### 1.2 语音+画面融合感知

#### 1.2.1 音频事件检测 (Audio Event Detection)

用于检测教学场景中的关键音频事件：
- **语音开始/结束**: VAD (Voice Activity Detection)
- **关键词触发**: "请看", "注意", "总结" 等
- **环境音**: 掌声、铃声、噪声

**轻量 AED 方案**:

| 模型 | 参数量 | 显存 | 延迟 | 适用场景 |
|------|--------|------|------|----------|
| YAMNet | 3.7M | ~100MB | ~10ms | 通用音频事件 |
| AudioSet VGGish | 62M | ~300MB | ~20ms | 预训练特征 |
| PANNs CNN14 | 79M | ~400MB | ~30ms | 高精度检测 |
| Whisper VAD | 39M | ~500MB | ~50ms | 语音专用 |

**实现建议**:
```python
import torch
import torchaudio

# Silero VAD (轻量且准确)
model, utils = torch.hub.load(
    repo_or_dir='snakers4/silero-vad',
    model='silero_vad',
    force_reload=True
)
(get_speech_timestamps, save_audio, read_audio, 
 VADIterator, collect_chunks) = utils

# 实时 VAD
vad_iterator = VADIterator(model)
```

#### 1.2.2 ASR 与画面时间对齐

**ASR 方案对比**:

| 方案 | 模型大小 | 显存 | RTF | 准确率 (WER) |
|------|----------|------|-----|--------------|
| Faster-Whisper tiny | 39M | ~500MB | 0.05 | ~18% |
| Faster-Whisper base | 74M | ~1GB | 0.1 | ~14% |
| Faster-Whisper small | 244M | ~2GB | 0.15 | ~10% |
| Whisper.cpp tiny | 39M | ~100MB | 0.08 | ~19% |
| Distil-Whisper | 756M | ~3GB | 0.2 | ~11% |

**时间对齐策略**:
1. **时间戳对齐**: ASR 输出带时间戳的文本
2. **滑动窗口**: 2-5 秒的音频窗口与对应视频帧对齐
3. **关键帧触发**: 检测到语音时提取对应视频帧

```python
from faster_whisper import WhisperModel

# 轻量 ASR 配置
model = WhisperModel(
    "tiny",  # 或 "base" 根据资源调整
    device="cuda",
    compute_type="int8_float16"  # 混合精度
)

# 带时间戳转录
segments, info = model.transcribe(
    "audio.wav",
    beam_size=5,
    word_timestamps=True  # 启用词级时间戳
)
```

#### 1.2.3 多模态融合策略

**早期融合 (Early Fusion)**:
- 在特征层面融合音频和视频特征
- 优势: 可以学习跨模态关联
- 劣势: 计算量大，需要大量训练数据
- **适用**: 云端深度理解

**晚期融合 (Late Fusion)**:
- 分别处理音频和视频，在决策层融合
- 优势: 模块化，易于维护
- 劣势: 可能丢失跨模态信息
- **适用**: 边缘触发决策

**混合融合 (Hybrid Fusion)**:
- 边缘侧晚期融合做触发决策
- 云端早期融合做深度理解

```python
# 晚期融合示例
class MultimodalTrigger:
    def __init__(self):
        self.video_detector = VideoChangeDetector()
        self.audio_detector = AudioEventDetector()
        self.asr = ASRProcessor()
    
    def process(self, video_frame, audio_chunk):
        # 独立处理
        video_score = self.video_detector.detect(video_frame)
        audio_events = self.audio_detector.detect(audio_chunk)
        
        # 决策层融合
        trigger_score = self.fusion_logic(video_score, audio_events)
        
        return trigger_score > self.threshold
```

---

## 2. 边云协同架构设计

### 2.1 边侧（持续在线，低功耗）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              边侧设备 (12GB VRAM)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        输入层                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │   视频流     │  │   音频流     │  │   系统状态   │              │   │
│  │  │  (1080p@5fps)│  │  (16kHz)     │  │  (CPU/GPU)   │              │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │   │
│  │         │                 │                 │                       │   │
│  └─────────┼─────────────────┼─────────────────┼───────────────────────┘   │
│            │                 │                 │                            │
│            ▼                 ▼                 ▼                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      轻量感知层 (实时处理)                           │   │
│  │                                                                     │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │   │
│  │  │  光流变化检测   │  │  YOLO 目标检测  │  │   VAD 语音检测  │     │   │
│  │  │  (LK算法)       │  │  (YOLOv8n)      │  │  (Silero VAD)   │     │   │
│  │  │  ~2ms/帧        │  │  ~2ms/帧        │  │  ~10ms/块       │     │   │
│  │  │  <100MB VRAM    │  │  ~300MB VRAM    │  │  ~100MB VRAM    │     │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │   │
│  │           │                    │                    │              │   │
│  │           └────────────────────┼────────────────────┘              │   │
│  │                                ▼                                   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │              OCR 变化检测 (课件场景专用)                      │  │   │
│  │  │  • 文本区域检测 (DBNet)                                      │  │   │
│  │  │  • 文本识别 (SVTR)                                           │  │   │
│  │  │  • 内容变化对比                                              │  │   │
│  │  │  ~100ms/帧, ~500MB VRAM                                      │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            │                                                                │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      触发决策层                                     │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              变化重要性评分引擎                              │   │   │
│  │  │                                                             │   │   │
│  │  │  评分维度:                                                  │   │   │
│  │  │  • 变化幅度 (光流/像素差异)        × 0.25                   │   │   │
│  │  │  • 内容重要性 (YOLO 检测结果)      × 0.25                   │   │   │
│  │  │  • 文本变化 (OCR 编辑距离)         × 0.30                   │   │   │
│  │  │  • 语音触发 (关键词/语调)          × 0.20                   │   │   │
│  │  │                                                             │   │   │
│  │  │  输出: importance_score (0-1)                               │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              噪声过滤策略                                    │   │   │
│  │  │                                                             │   │   │
│  │  │  • 时间窗口去抖 (连续 3 帧确认)                              │   │   │
│  │  │  • 最小变化阈值 (过滤微小抖动)                               │   │   │
│  │  │  • 重复内容过滤 (相似度 > 0.9 跳过)                          │   │   │
│  │  │  • 冷却期机制 (触发后 2s 内不重复)                           │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            │                                                                │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      轻量理解层 (按需加载)                           │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  MiniCPM-V 4.0 (INT4)                                       │   │   │
│  │  │  • 显存占用: ~4GB                                           │   │   │
│  │  │  • 推理延迟: ~500ms/帧                                      │   │   │
│  │  │  • 功能: 基础画面理解、OCR、简单问答                         │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            │                                                                │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      通信层                                         │   │
│  │  • WebSocket 长连接                                                 │   │
│  │  • 压缩传输 (JPEG 质量 85, 音频 Opus)                                │   │
│  │  • 心跳检测 (30s 间隔)                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 云端（按需唤醒，高质量）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              云端服务器                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      触发条件评估                                   │   │
│  │                                                                     │   │
│  │  触发条件 (满足任一):                                               │   │
│  │  1. importance_score > 0.7 (边侧评分)                               │   │
│  │  2. 语音关键词匹配 ("总结", "重点", "注意")                          │   │
│  │  3. 用户主动查询                                                    │   │
│  │  4. 周期性唤醒 (每 30s 检查一次)                                    │   │
│  │                                                                     │   │
│  │  防抖动: 同一内容 10s 内不重复触发                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            │                                                                │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      深度理解层                                     │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  全量 VLM (Qwen2-VL-72B / GPT-4V / Claude-3)                │   │   │
│  │  │  • 课件内容深度解析                                          │   │   │
│  │  │  • 知识点提取与关联                                          │   │   │
│  │  │  • 教学意图理解                                              │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  多模态融合分析                                              │   │   │
│  │  │  • 音频文本 + 画面内容联合理解                                │   │   │
│  │  │  • 时间轴对齐与事件关联                                       │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            │                                                                │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      响应生成层                                     │   │
│  │  • 学习建议生成                                                     │   │
│  │  • 知识点补充                                                       │   │
│  │  • 互动问题生成                                                     │   │
│  │  • 笔记结构化                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 边云协同数据流

```
┌──────────────┐         持续视频/音频流          ┌──────────────┐
│   摄像头/    │ ───────────────────────────────► │    边侧      │
│   麦克风     │                                  │   设备       │
└──────────────┘                                  └──────┬───────┘
                                                         │
                              ┌──────────────────────────┼──────────────────────────┐
                              │                          │                          │
                              ▼                          ▼                          ▼
                    ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
                    │  光流变化检测   │        │  YOLO 目标检测  │        │   VAD 语音检测  │
                    │  (实时, 5fps)   │        │  (实时, 5fps)   │        │  (实时, 16kHz)  │
                    └────────┬────────┘        └────────┬────────┘        └────────┬────────┘
                             │                          │                          │
                             └──────────────────────────┼──────────────────────────┘
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │  重要性评分计算  │
                                              │  (每 200ms)     │
                                              └────────┬────────┘
                                                       │
                              ┌────────────────────────┼────────────────────────┐
                              │                        │                        │
                              ▼                        ▼                        ▼
                    ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
                    │ score < 0.3     │      │ 0.3 ≤ score < 0.7│      │   score ≥ 0.7   │
                    │   (忽略)        │      │  (本地轻量理解)  │      │  (触发云端)     │
                    └─────────────────┘      └────────┬────────┘      └────────┬────────┘
                                                      │                        │
                                                      ▼                        ▼
                                            ┌─────────────────┐      ┌─────────────────┐
                                            │ MiniCPM-V 4.0   │      │  压缩帧 + ASR   │
                                            │ INT4 推理       │      │  文本上传       │
                                            │ (基础理解)      │      │                 │
                                            └────────┬────────┘      └────────┬────────┘
                                                     │                        │
                                                     ▼                        ▼
                                           ┌─────────────────┐      ┌─────────────────┐
                                           │  本地缓存结果   │      │    云端服务器   │
                                           │  (供快速查询)   │      │                 │
                                           └─────────────────┘      │  • 深度理解     │
                                                                    │  • 知识生成     │
                                                                    │  • 响应推送     │
                                                                    └─────────────────┘
```

---

## 3. 12GB VRAM 可行方案

### 3.1 VLM 模型选型与显存预算

**显存分配建议**:

| 组件 | 显存占用 | 说明 |
|------|----------|------|
| 系统预留 | 1GB | CUDA 上下文等 |
| 光流检测 | 0.1GB | Lucas-Kanade |
| YOLO 检测 | 0.3GB | YOLOv8n |
| OCR 检测 | 0.5GB | PaddleOCR 轻量版 |
| VAD | 0.1GB | Silero VAD |
| ASR (可选) | 1GB | Faster-Whisper base |
| VLM (边侧) | 4-6GB | MiniCPM-V 4.0 INT4 |
| 缓冲/其他 | 1GB | 帧缓冲等 |
| **总计** | **~8-10GB** | 留 2-4GB 余量 |

### 3.2 光流法 vs 检测法资源对比

| 方法 | CPU 占用 | GPU 显存 | 延迟 | 准确率 | 适用场景 |
|------|----------|----------|------|--------|----------|
| LK 稀疏光流 | 低 | <100MB | ~2ms | 中 | 运动检测 |
| Farneback 稠密光流 | 中 | ~200MB | ~20ms | 中高 | 全画面分析 |
| RAFT 光流 | 高 | ~1GB | ~80ms | 高 | 精确运动 |
| YOLOv8n 检测 | 低 | ~300MB | ~2ms | 高 | 目标变化 |
| YOLOv8s 检测 | 中 | ~500MB | ~3ms | 很高 | 精细检测 |
| 帧差法 | 极低 | <50MB | ~1ms | 低 | 简单监控 |

**推荐组合**:
- **课件场景**: LK 光流 + OCR 变化检测
- **会议场景**: YOLOv8n (人物检测) + VAD
- **混合场景**: LK 光流 + YOLOv8n + OCR

### 3.3 模型量化方案详解

**AWQ 量化 (推荐)**:
```python
# AWQ 量化模型加载
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

model = AutoAWQForCausalLM.from_quantized(
    "Qwen/Qwen2-VL-7B-Instruct-AWQ",
    device_map="auto"
)
```

**bitsandbytes INT4**:
```python
from transformers import BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True
)

model = AutoModel.from_pretrained(
    model_path,
    quantization_config=quantization_config,
    device_map="auto"
)
```

**TensorRT 加速**:
```python
# YOLO TensorRT 导出
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.export(format='engine', int8=True, workspace=2)  # 2GB 工作空间
```

### 3.4 帧率与延迟权衡

**推荐配置**:

| 场景 | 视频帧率 | 音频采样 | 边侧延迟 | 云端触发 |
|------|----------|----------|----------|----------|
| 实时课件 | 5 fps | 16kHz | <200ms | 重要性>0.7 |
| 会议记录 | 2 fps | 16kHz | <300ms | 关键词触发 |
| 直播教学 | 10 fps | 16kHz | <150ms | 实时触发 |
| 离线分析 | 1 fps | 16kHz | <500ms | 批量处理 |

**延迟优化策略**:
1. **异步处理**: 视频解码与推理并行
2. **帧跳过**: 无变化时跳过推理
3. **分辨率自适应**: 根据内容动态调整分辨率
4. **批处理**: 多帧合并推理（云端）

---

## 4. 实际产品/开源项目参考

### 4.1 教育/会议领域方案

**LiveCaptions (Windows 11)**
- 本地 ASR + 实时字幕
- 技术栈: ONNX Runtime, Whisper 轻量版
- 特点: 完全离线，低延迟

**Microsoft Teams 智能回顾**
- 语音识别 + 画面内容提取
- 边云协同架构
- 技术栈: Azure Cognitive Services

**Otter.ai**
- 会议转录 + 关键信息提取
- 云端 ASR + NLP
- 支持说话人分离

**Notion AI / Obsidian 插件**
- 笔记整理 + 知识图谱
- 集成多模态理解

### 4.2 边缘 AI 设备项目

**NVIDIA Jetson 生态**:

| 项目 | 功能 | 硬件要求 |
|------|------|----------|
| jetson-inference | 图像分类/检测/分割 | Jetson Nano 及以上 |
| NanoOWL | 开放词汇检测 | Jetson Orin |
| Live Llava | 实时 VLM 对话 | Jetson AGX Orin |
| jetson-voice | 语音处理 | Jetson Nano 及以上 |

**RK3588 生态**:
- **RKNN Toolkit**: 模型转换与部署
- **NPU 算力**: 6 TOPS
- **支持模型**: YOLO, ResNet, MobileNet 等

**参考项目**:
```
GitHub: dusty-nv/jetson-inference
- 实时图像分类、检测、分割
- TensorRT 加速
- 支持 ROS/ROS2

GitHub: NVIDIA-AI-IOT/nanoowl
- 开放词汇目标检测
- CLIP + ViT 架构
- 边缘实时运行
```

### 4.3 开源项目代码参考

**LiveCaptions (类 Unix)**:
- 仓库: `github/abb128/LiveCaptions`
- 功能: 实时语音识别 + 字幕显示
- 技术: Whisper.cpp, GTK4

**MeetingAssist**:
- 概念项目: 会议助手
- 功能: 转录 + 摘要 + 行动项提取
- 技术: Whisper + LLM

**ClassAnalytics**:
- 教育分析工具
- 功能: 学生参与度分析
- 技术: OpenPose + 行为识别

**OpenAI Whisper**:
- 仓库: `github/openai/whisper`
- 功能: 通用语音识别
- 多语言支持，多种模型尺寸

**Faster-Whisper**:
- 仓库: `github/SYSTRAN/faster-whisper`
- 优化: CTranslate2 加速
- 量化: 支持 INT8，显存节省 40%

---

## 5. 技术对比表

### 5.1 画面变化检测方法对比

| 方法 | 显存需求 | 延迟 (1080p) | 准确率 | 适用场景 | 推荐指数 |
|------|----------|--------------|--------|----------|----------|
| **LK 稀疏光流** | <100MB | ~2ms | ⭐⭐⭐ | 运动检测、触发器 | ⭐⭐⭐⭐⭐ |
| **Farneback 光流** | ~200MB | ~20ms | ⭐⭐⭐⭐ | 全画面分析 | ⭐⭐⭐⭐ |
| **RAFT 光流** | ~1GB | ~80ms | ⭐⭐⭐⭐⭐ | 精确运动分析 | ⭐⭐⭐ |
| **YOLOv8n** | ~300MB | ~2ms | ⭐⭐⭐⭐ | 目标检测 | ⭐⭐⭐⭐⭐ |
| **YOLOv8s** | ~500MB | ~3ms | ⭐⭐⭐⭐⭐ | 精细检测 | ⭐⭐⭐⭐ |
| **OCR 变化检测** | ~500MB | ~100ms | ⭐⭐⭐⭐⭐ | 课件场景 | ⭐⭐⭐⭐⭐ |
| **帧差法** | <50MB | ~1ms | ⭐⭐ | 简单监控 | ⭐⭐⭐ |

### 5.2 VLM 模型 12GB VRAM 可行性对比

| 模型 | FP16 显存 | INT4 显存 | 推理延迟 | OCR 能力 | 推荐指数 |
|------|-----------|-----------|----------|----------|----------|
| **MiniCPM-V 4.0** | ~10GB | ~4GB | ~300ms | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Qwen2-VL-2B** | ~5GB | ~2.5GB | ~150ms | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Qwen2.5-VL-3B** | ~7GB | ~3GB | ~200ms | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **LLaVA-Phi-3** | ~8GB | ~3.5GB | ~250ms | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **InternVL2-4B** | ~9GB | ~4GB | ~280ms | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| MiniCPM-V 2.6 | ~18GB | ~6GB | ~500ms | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Qwen2-VL-7B | ~16GB | ~6GB | ~400ms | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| LLaVA-v1.5-7B | ~16GB | ~6GB | ~450ms | ⭐⭐⭐⭐ | ⭐⭐⭐ |

### 5.3 量化方案对比

| 量化方法 | 精度损失 | 速度提升 | 显存节省 | 易用性 | 推荐指数 |
|----------|----------|----------|----------|--------|----------|
| **AWQ** | 低 | 1.5x | 60% | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **GPTQ** | 低 | 1.3x | 60% | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **bitsandbytes** | 中 | 1.2x | 50% | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **SmoothQuant** | 低 | 1.4x | 55% | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **torchao INT4** | 中 | 1.6x | 70% | ⭐⭐⭐ | ⭐⭐⭐⭐ |

### 5.4 ASR 方案对比

| 方案 | 模型大小 | 显存 | RTF | WER | 推荐指数 |
|------|----------|------|-----|-----|----------|
| **Faster-Whisper tiny** | 39M | ~500MB | 0.05 | ~18% | ⭐⭐⭐⭐ |
| **Faster-Whisper base** | 74M | ~1GB | 0.1 | ~14% | ⭐⭐⭐⭐⭐ |
| Faster-Whisper small | 244M | ~2GB | 0.15 | ~10% | ⭐⭐⭐⭐ |
| Whisper.cpp tiny | 39M | ~100MB | 0.08 | ~19% | ⭐⭐⭐⭐ |
| Distil-Whisper | 756M | ~3GB | 0.2 | ~11% | ⭐⭐⭐ |

---

## 6. 推荐配置与代码示例

### 6.1 12GB VRAM 推荐配置

**硬件配置**:
```yaml
GPU: NVIDIA RTX 3060 12GB / RTX 4070 12GB / T4 16GB
CPU: 8 核以上
RAM: 32GB
存储: SSD 100GB+
```

**软件栈**:
```yaml
CUDA: 12.1+
PyTorch: 2.1+
TensorRT: 8.6+
ONNX Runtime: 1.16+
OpenCV: 4.8+
```

**模型配置**:
```yaml
# 边侧常驻模型
光流检测: LK 稀疏光流 (<100MB)
目标检测: YOLOv8n INT8 TensorRT (~300MB)
OCR: PaddleOCR 轻量版 (~500MB)
VAD: Silero VAD (~100MB)
ASR: Faster-Whisper base INT8 (~1GB)

# 边侧按需加载 VLM
VLM: MiniCPM-V 4.0 INT4 (~4GB)
备选: Qwen2.5-VL-3B INT4 (~3GB)

# 云端模型
VLM: Qwen2-VL-72B / GPT-4V
```

### 6.2 完整代码示例

#### 6.2.1 边侧变化检测服务

```python
"""
边侧画面变化检测服务
适用于 12GB VRAM 环境
"""

import cv2
import numpy as np
import torch
from dataclasses import dataclass
from typing import Optional, List, Tuple
from queue import Queue
import threading
import time


@dataclass
class ChangeDetectionResult:
    """变化检测结果"""
    has_change: bool
    importance_score: float
    change_type: str  # 'motion', 'object', 'text', 'audio'
    regions: List[Tuple[int, int, int, int]]  # 变化区域坐标
    metadata: dict


class OpticalFlowDetector:
    """LK 稀疏光流变化检测器"""
    
    def __init__(self, 
                 max_corners: int = 100,
                 quality_level: float = 0.3,
                 min_distance: int = 7,
                 threshold: float = 1.0):
        self.max_corners = max_corners
        self.quality_level = quality_level
        self.min_distance = min_distance
        self.threshold = threshold
        
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
        self.prev_gray = None
        self.prev_points = None
    
    def detect(self, frame: np.ndarray) -> Tuple[bool, float, List]:
        """
        检测画面变化
        
        Returns:
            (是否有变化, 变化强度, 变化区域)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.prev_gray is None:
            self.prev_gray = gray
            self.prev_points = cv2.goodFeaturesToTrack(
                gray, self.max_corners, self.quality_level, self.min_distance
            )
            return False, 0.0, []
        
        if self.prev_points is None or len(self.prev_points) < 10:
            self.prev_points = cv2.goodFeaturesToTrack(
                gray, self.max_corners, self.quality_level, self.min_distance
            )
            self.prev_gray = gray
            return False, 0.0, []
        
        # 计算光流
        curr_points, status, error = cv2.calcOpticalFlowPyrLK(
            self.prev_gray, gray, self.prev_points, None, **self.lk_params
        )
        
        if curr_points is None:
            self.prev_gray = gray
            return False, 0.0, []
        
        # 筛选有效点
        good_prev = self.prev_points[status == 1]
        good_curr = curr_points[status == 1]
        
        # 计算运动幅度
        if len(good_prev) > 0:
            motion = np.linalg.norm(good_curr - good_prev, axis=1)
            mean_motion = np.mean(motion)
            max_motion = np.max(motion) if len(motion) > 0 else 0
        else:
            mean_motion = 0
            max_motion = 0
        
        # 检测变化区域
        change_regions = []
        if len(good_curr) > 0:
            for i, (curr, prev) in enumerate(zip(good_curr, good_prev)):
                if status[i] == 1 and motion[i] > self.threshold:
                    x, y = int(curr[0]), int(curr[1])
                    change_regions.append((x-20, y-20, x+20, y+20))
        
        has_change = mean_motion > self.threshold
        importance = min(mean_motion / (self.threshold * 3), 1.0)
        
        # 更新状态
        self.prev_gray = gray
        self.prev_points = good_curr.reshape(-1, 1, 2)
        
        return has_change, importance, change_regions


class YOLOChangeDetector:
    """YOLO 目标变化检测器"""
    
    def __init__(self, model_path: str = 'yolov8n.pt', device: str = 'cuda'):
        from ultralytics import YOLO
        
        self.model = YOLO(model_path)
        self.device = device
        self.prev_detections = None
        self.iou_threshold = 0.5
    
    def detect(self, frame: np.ndarray) -> Tuple[bool, float, List]:
        """检测目标变化"""
        results = self.model(frame, verbose=False, device=self.device)
        
        current_detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                current_detections.append({
                    'class': cls,
                    'conf': conf,
                    'bbox': (x1, y1, x2, y2)
                })
        
        # 对比前后帧检测
        if self.prev_detections is None:
            self.prev_detections = current_detections
            return False, 0.0, []
        
        # 计算变化
        new_objects = self._find_new_objects(
            current_detections, self.prev_detections
        )
        
        importance = min(len(new_objects) * 0.2 + 
                        len(current_detections) * 0.05, 1.0)
        
        has_change = len(new_objects) > 0
        regions = [d['bbox'] for d in new_objects]
        
        self.prev_detections = current_detections
        
        return has_change, importance, regions
    
    def _find_new_objects(self, current, previous):
        """找出新出现的目标"""
        new_objects = []
        for curr in current:
            is_new = True
            for prev in previous:
                if curr['class'] == prev['class']:
                    iou = self._compute_iou(curr['bbox'], prev['bbox'])
                    if iou > self.iou_threshold:
                        is_new = False
                        break
            if is_new:
                new_objects.append(curr)
        return new_objects
    
    def _compute_iou(self, box1, box2):
        """计算 IoU"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0


class ImportanceScorer:
    """变化重要性评分引擎"""
    
    def __init__(self):
        # 权重配置
        self.weights = {
            'motion': 0.25,
            'object': 0.25,
            'text': 0.30,
            'audio': 0.20
        }
        
        # 去抖配置
        self.history = []
        self.history_size = 3
        self.cooldown = 2.0  # 秒
        self.last_trigger = 0
    
    def score(self, 
              motion_result: Optional[Tuple] = None,
              object_result: Optional[Tuple] = None,
              text_result: Optional[Tuple] = None,
              audio_result: Optional[Tuple] = None) -> float:
        """
        计算综合重要性评分
        
        Returns:
            0-1 之间的评分，>0.7 建议触发云端
        """
        scores = {}
        
        if motion_result:
            scores['motion'] = motion_result[1]
        if object_result:
            scores['object'] = object_result[1]
        if text_result:
            scores['text'] = text_result[1]
        if audio_result:
            scores['audio'] = audio_result[1]
        
        # 加权计算
        total_weight = sum(self.weights.get(k, 0) for k in scores.keys())
        if total_weight == 0:
            return 0.0
        
        weighted_score = sum(
            scores.get(k, 0) * self.weights[k] 
            for k in scores.keys()
        ) / total_weight
        
        # 历史平滑
        self.history.append(weighted_score)
        if len(self.history) > self.history_size:
            self.history.pop(0)
        
        smoothed_score = np.mean(self.history)
        
        # 冷却检查
        current_time = time.time()
        if current_time - self.last_trigger < self.cooldown:
            smoothed_score *= 0.5  # 冷却期内降低评分
        
        return min(smoothed_score, 1.0)
    
    def should_trigger_cloud(self, score: float) -> bool:
        """判断是否触发云端"""
        if score > 0.7:
            self.last_trigger = time.time()
            return True
        return False


class EdgeDetectionService:
    """边侧检测服务主类"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # 初始化检测器
        self.flow_detector = OpticalFlowDetector()
        self.yolo_detector = YOLOChangeDetector(
            model_path=self.config.get('yolo_model', 'yolov8n.pt')
        )
        self.scorer = ImportanceScorer()
        
        # 运行状态
        self.running = False
        self.frame_queue = Queue(maxsize=10)
        self.result_queue = Queue()
        
        # 性能统计
        self.stats = {
            'frames_processed': 0,
            'triggers': 0,
            'avg_latency': 0
        }
    
    def start(self):
        """启动服务"""
        self.running = True
        
        # 启动处理线程
        self.process_thread = threading.Thread(target=self._process_loop)
        self.process_thread.start()
        
        print("边侧检测服务已启动")
    
    def stop(self):
        """停止服务"""
        self.running = False
        self.process_thread.join()
        print("边侧检测服务已停止")
    
    def _process_loop(self):
        """主处理循环"""
        while self.running:
            if not self.frame_queue.empty():
                frame = self.frame_queue.get()
                
                start_time = time.time()
                
                # 并行检测
                flow_result = self.flow_detector.detect(frame)
                yolo_result = self.yolo_detector.detect(frame)
                
                # 计算重要性
                importance = self.scorer.score(
                    motion_result=flow_result,
                    object_result=yolo_result
                )
                
                # 判断触发
                should_trigger = self.scorer.should_trigger_cloud(importance)
                
                latency = time.time() - start_time
                
                # 更新统计
                self.stats['frames_processed'] += 1
                if should_trigger:
                    self.stats['triggers'] += 1
                
                # 保存结果
                result = ChangeDetectionResult(
                    has_change=flow_result[0] or yolo_result[0],
                    importance_score=importance,
                    change_type='mixed',
                    regions=flow_result[2] + yolo_result[2],
                    metadata={
                        'latency': latency,
                        'trigger_cloud': should_trigger
                    }
                )
                self.result_queue.put(result)
                
                # 打印日志
                if self.stats['frames_processed'] % 30 == 0:
                    print(f"处理帧数: {self.stats['frames_processed']}, "
                          f"触发次数: {self.stats['triggers']}, "
                          f"延迟: {latency*1000:.1f}ms")
            else:
                time.sleep(0.01)
    
    def process_frame(self, frame: np.ndarray) -> Optional[ChangeDetectionResult]:
        """处理单帧"""
        if self.frame_queue.full():
            self.frame_queue.get()  # 丢弃最旧帧
        
        self.frame_queue.put(frame)
        
        # 非阻塞获取结果
        if not self.result_queue.empty():
            return self.result_queue.get()
        return None


# 使用示例
if __name__ == "__main__":
    # 创建服务
    service = EdgeDetectionService({
        'yolo_model': 'yolov8n.pt'
    })
    
    service.start()
    
    # 模拟视频流
    cap = cv2.VideoCapture(0)  # 或使用视频文件
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 处理帧
            result = service.process_frame(frame)
            
            if result and result.metadata.get('trigger_cloud'):
                print(f"触发云端处理! 重要性: {result.importance_score:.2f}")
                # TODO: 发送到云端
            
            # 显示 (调试用)
            cv2.imshow('Edge Detection', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        service.stop()
        cap.release()
        cv2.destroyAllWindows()
```

#### 6.2.2 VLM 边侧推理示例

```python
"""
MiniCPM-V 4.0 边侧推理示例
INT4 量化，适用于 12GB VRAM
"""

import torch
from PIL import Image
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig
import cv2
import numpy as np


class EdgeVLM:
    """边侧 VLM 推理引擎"""
    
    def __init__(self, 
                 model_path: str = 'openbmb/MiniCPM-V-4.0',
                 use_quantization: bool = True,
                 device: str = 'cuda'):
        self.device = device
        
        # 量化配置
        if use_quantization:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True
            )
            
            self.model = AutoModel.from_pretrained(
                model_path,
                trust_remote_code=True,
                quantization_config=quantization_config,
                device_map='auto',
                torch_dtype=torch.float16
            )
        else:
            self.model = AutoModel.from_pretrained(
                model_path,
                trust_remote_code=True,
                torch_dtype=torch.float16
            ).to(device)
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )
        
        self.model.eval()
        print(f"VLM 模型加载完成，显存占用: {torch.cuda.memory_allocated()/1e9:.2f}GB")
    
    def analyze_frame(self, 
                      frame: np.ndarray,
                      question: str = "描述这张图片的内容") -> str:
        """
        分析视频帧
        
        Args:
            frame: OpenCV 格式的帧 (BGR)
            question: 询问内容
        
        Returns:
            模型回答
        """
        # 转换格式
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        # 构建对话
        msgs = [{'role': 'user', 'content': [image, question]}]
        
        # 推理
        with torch.no_grad():
            res = self.model.chat(
                image=None,
                msgs=msgs,
                tokenizer=self.tokenizer,
                sampling=True,
                temperature=0.7
            )
        
        return res
    
    def analyze_ppt_slide(self, frame: np.ndarray) -> dict:
        """
        专门分析 PPT 课件内容
        
        Returns:
            结构化分析结果
        """
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        # 多轮提问获取全面信息
        questions = [
            "这张幻灯片的主要内容是什么？",
            "列出这张幻灯片中的所有文本内容",
            "这张幻灯片中有哪些图表或图片？",
            "这张幻灯片的关键知识点是什么？"
        ]
        
        results = {}
        for q in questions:
            msgs = [{'role': 'user', 'content': [image, q]}]
            with torch.no_grad():
                res = self.model.chat(
                    image=None,
                    msgs=msgs,
                    tokenizer=self.tokenizer,
                    sampling=False
                )
            results[q] = res
        
        return results
    
    def batch_analyze(self, 
                      frames: list,
                      question: str = "描述内容") -> list:
        """
        批量分析 (节省显存)
        """
        results = []
        for frame in frames:
            result = self.analyze_frame(frame, question)
            results.append(result)
            
            # 清理显存
            torch.cuda.empty_cache()
        
        return results


# 使用示例
if __name__ == "__main__":
    # 初始化模型
    vlm = EdgeVLM(
        model_path='openbmb/MiniCPM-V-4.0',
        use_quantization=True
    )
    
    # 读取测试图像
    frame = cv2.imread('test_slide.jpg')
    
    # 分析课件
    result = vlm.analyze_ppt_slide(frame)
    
    for question, answer in result.items():
        print(f"\nQ: {question}")
        print(f"A: {answer}")
```

#### 6.2.3 边云协同通信示例

```python
"""
边云协同通信模块
WebSocket 长连接，支持压缩传输
"""

import asyncio
import websockets
import json
import zlib
import base64
from dataclasses import dataclass, asdict
from typing import Callable, Optional
import cv2
import numpy as np


@dataclass
class EdgePayload:
    """边侧上传数据包"""
    timestamp: float
    importance_score: float
    trigger_reason: str
    frame_data: Optional[str]  # base64 编码的压缩图像
    asr_text: Optional[str]
    metadata: dict


@dataclass
class CloudResponse:
    """云端响应数据包"""
    timestamp: float
    analysis_result: str
    knowledge_points: list
    suggestions: list
    confidence: float


class EdgeCloudBridge:
    """边云协同通信桥"""
    
    def __init__(self, 
                 cloud_url: str = 'ws://localhost:8765',
                 compression_quality: int = 85):
        self.cloud_url = cloud_url
        self.compression_quality = compression_quality
        self.websocket = None
        self.connected = False
        self.on_response: Optional[Callable] = None
    
    async def connect(self):
        """建立连接"""
        try:
            self.websocket = await websockets.connect(self.cloud_url)
            self.connected = True
            print(f"已连接到云端: {self.cloud_url}")
            
            # 启动接收循环
            asyncio.create_task(self._receive_loop())
            
        except Exception as e:
            print(f"连接失败: {e}")
            self.connected = False
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
    
    def compress_frame(self, frame: np.ndarray) -> str:
        """
        压缩图像帧
        
        1. 调整分辨率 (720p)
        2. JPEG 压缩
        3. zlib 压缩
        4. base64 编码
        """
        # 调整分辨率
        h, w = frame.shape[:2]
        if h > 720:
            scale = 720 / h
            new_w = int(w * scale)
            frame = cv2.resize(frame, (new_w, 720))
        
        # JPEG 压缩
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.compression_quality]
        _, encoded = cv2.imencode('.jpg', frame, encode_param)
        
        # zlib 压缩
        compressed = zlib.compress(encoded.tobytes(), level=6)
        
        # base64 编码
        return base64.b64encode(compressed).decode('utf-8')
    
    async def send_trigger(self, 
                          frame: np.ndarray,
                          importance_score: float,
                          asr_text: Optional[str] = None,
                          metadata: dict = None):
        """
        发送触发请求到云端
        """
        if not self.connected:
            print("未连接到云端，跳过发送")
            return
        
        # 压缩图像
        compressed_frame = self.compress_frame(frame)
        
        # 构建数据包
        payload = EdgePayload(
            timestamp=asyncio.get_event_loop().time(),
            importance_score=importance_score,
            trigger_reason='importance_threshold',
            frame_data=compressed_frame,
            asr_text=asr_text,
            metadata=metadata or {}
        )
        
        # 发送
        try:
            await self.websocket.send(json.dumps(asdict(payload)))
            print(f"已发送触发请求，重要性: {importance_score:.2f}")
        except Exception as e:
            print(f"发送失败: {e}")
            self.connected = False
    
    async def _receive_loop(self):
        """接收云端响应循环"""
        while self.connected and self.websocket:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                response = CloudResponse(
                    timestamp=data['timestamp'],
                    analysis_result=data['analysis_result'],
                    knowledge_points=data.get('knowledge_points', []),
                    suggestions=data.get('suggestions', []),
                    confidence=data.get('confidence', 0.0)
                )
                
                if self.on_response:
                    self.on_response(response)
                    
            except websockets.exceptions.ConnectionClosed:
                print("云端连接已关闭")
                self.connected = False
                break
            except Exception as e:
                print(f"接收错误: {e}")


# 云端服务器示例
class CloudServer:
    """云端处理服务器示例"""
    
    def __init__(self):
        self.clients = set()
    
    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        self.clients.add(websocket)
        print(f"新客户端连接: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                # 解析数据
                data = json.loads(message)
                payload = EdgePayload(**data)
                
                print(f"收到触发请求，重要性: {payload.importance_score:.2f}")
                
                # 解码图像
                if payload.frame_data:
                    frame = self.decompress_frame(payload.frame_data)
                    
                    # TODO: 调用全量 VLM 进行深度分析
                    analysis_result = self.analyze_with_vlm(
                        frame, 
                        payload.asr_text
                    )
                    
                    # 发送响应
                    response = CloudResponse(
                        timestamp=asyncio.get_event_loop().time(),
                        analysis_result=analysis_result,
                        knowledge_points=["知识点1", "知识点2"],
                        suggestions=["建议1", "建议2"],
                        confidence=0.85
                    )
                    
                    await websocket.send(json.dumps(asdict(response)))
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"客户端断开: {websocket.remote_address}")
        finally:
            self.clients.remove(websocket)
    
    def decompress_frame(self, frame_data: str) -> np.ndarray:
        """解压图像帧"""
        # base64 解码
        compressed = base64.b64decode(frame_data)
        
        # zlib 解压
        jpg_data = zlib.decompress(compressed)
        
        # 解码 JPEG
        nparr = np.frombuffer(jpg_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return frame
    
    def analyze_with_vlm(self, frame: np.ndarray, asr_text: Optional[str]) -> str:
        """
        使用全量 VLM 分析
        
        这里可以调用:
        - Qwen2-VL-72B
        - GPT-4V
        - Claude-3
        """
        # TODO: 实现 VLM 调用
        return "深度分析结果..."
    
    async def start(self, host: str = '0.0.0.0', port: int = 8765):
        """启动服务器"""
        print(f"启动云端服务器: {host}:{port}")
        async with websockets.serve(self.handle_client, host, port):
            await asyncio.Future()  # 永久运行


# 使用示例
async def main():
    """测试边云协同"""
    
    # 启动云端服务器 (实际部署时单独运行)
    # server = CloudServer()
    # await server.start()
    
    # 边侧客户端
    bridge = EdgeCloudBridge('ws://localhost:8765')
    await bridge.connect()
    
    # 模拟发送触发
    frame = cv2.imread('test.jpg')
    await bridge.send_trigger(
        frame=frame,
        importance_score=0.85,
        asr_text="这是语音转录的文本",
        metadata={'scene': 'classroom'}
    )
    
    # 保持运行
    await asyncio.sleep(10)
    await bridge.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
```

### 6.3 部署配置示例

#### 6.3.1 Docker 部署配置

```dockerfile
# Dockerfile.edge
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

WORKDIR /app

# 安装依赖
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 运行
CMD ["python3", "edge_service.py"]
```

```txt
# requirements.txt
torch==2.1.0
torchvision==0.16.0
opencv-python==4.8.1
ultralytics==8.0.200
transformers==4.35.0
accelerate==0.24.0
bitsandbytes==0.41.0
websockets==12.0
pillow==10.1.0
numpy==1.24.3
```

#### 6.3.2 TensorRT 导出脚本

```python
"""
TensorRT 模型导出脚本
用于加速 YOLO 等模型在边缘设备的推理
"""

from ultralytics import YOLO

def export_yolo_tensorrt():
    """导出 YOLO 模型为 TensorRT 格式"""
    
    # 加载模型
    model = YOLO('yolov8n.pt')
    
    # 导出为 TensorRT INT8
    model.export(
        format='engine',
        device=0,
        half=True,  # FP16
        int8=True,  # INT8 量化
        workspace=4,  # 4GB 工作空间
        imgsz=640
    )
    
    print("TensorRT 模型导出完成")

if __name__ == "__main__":
    export_yolo_tensorrt()
```

---

## 7. 总结与建议

### 7.1 推荐技术栈

**边侧 (12GB VRAM)**:
- 变化检测: LK 光流 + YOLOv8n INT8
- OCR: PaddleOCR 轻量版
- VAD: Silero VAD
- ASR: Faster-Whisper base INT8
- VLM: MiniCPM-V 4.0 INT4

**云端**:
- VLM: Qwen2-VL-72B / GPT-4V
- 存储: 向量数据库 (Milvus/Pinecone)
- 缓存: Redis

### 7.2 性能预期

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 边侧延迟 | <200ms | 变化检测到评分输出 |
| 云端响应 | <2s | 触发到响应返回 |
| 显存占用 | <10GB | 边侧总占用 |
| 帧率 | 5fps | 视频分析帧率 |
| 准确率 | >85% | 重要变化检测准确率 |

### 7.3 后续优化方向

1. **模型蒸馏**: 将云端大模型知识蒸馏到边侧小模型
2. **自适应帧率**: 根据内容动态调整分析帧率
3. **增量学习**: 边侧模型持续学习用户习惯
4. **联邦学习**: 多设备协同训练，保护隐私

---

*文档生成时间: 2026年3月25日*
*适用环境: NVIDIA GPU 12GB VRAM*
