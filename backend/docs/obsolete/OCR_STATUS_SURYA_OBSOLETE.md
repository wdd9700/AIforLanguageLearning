# OCR（Surya）历史说明（已弃用）

说明：本文件为历史归档。当前工程 OCR 主线已切换为 PaddleOCR；此处保留 Surya 相关问题分析与旧集成记录，避免未来排查时信息丢失。

---

# OCR 服务集成说明

## 状态: ⏸️ 已集成但禁用

OCR 服务代码已完全集成到 backend,但由于 **Surya OCR 0.17.0 的模型下载 bug** 暂时禁用。

## 问题描述

### 1. 模型下载冲突 Bug

**错误信息**:
```
shutil.Error: Destination path 'C:\Users\74090\AppData\Local\datalab\datalab\Cache\models\text_detection/2025_05_07\.gitattributes' already exists
```

**原因**:
- Surya 0.17.0 的模型下载代码 (`surya/common/s3.py`) 存在并发下载 bug
- 多个文件同时下载时,临时文件移动到目标目录会产生冲突
- 重试机制无法解决 (每次重试都重新触发冲突)

### 2. 网络不稳定

**错误信息**:
```
SSLError: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol
```

**原因**:
- 模型服务器 `models.datalab.to` 连接不稳定
- 大文件下载 (73.4MB) 容易中断
- 与上述 bug 组合导致无法成功下载

## 已完成的集成

### 代码集成 ✅

**文件**: `backend/scripts/surya_ocr_wrapper.py`

```python
from surya.detection import DetectionPredictor
from surya.recognition import RecognitionPredictor
from surya.input.load import load_from_file

# 1. 文本检测
det_predictor = DetectionPredictor()
det_predictions = det_predictor(images)

# 2. 文本识别
rec_predictor = RecognitionPredictor()
rec_predictions = rec_predictor(images, det_predictions, [langs])
```

**特性**:
- ✅ 使用 Surya 0.17.0 最新 API
- ✅ 支持中英文混合识别
- ✅ CUDA GPU 加速
- ✅ JSON 输出格式
- ✅ 置信度和边界框信息

### 配置集成 ✅

**文件**: `backend/src/config/env.ts`

```typescript
ocr: {
  pythonPath: 'C:/Users/74090/Miniconda3/python.exe',
  scriptPath: path.join(__dirname, '../../scripts/surya_ocr_wrapper.py'),
  device: 'cuda', // cuda/cpu
  timeout: 60000,
  langs: 'zh,en',
  enabled: false, // ⏸️ 暂时禁用
}
```

### API 集成 ✅

**文件**: `backend/src/managers/service-manager.ts`

```typescript
async invokeOCR(imageBase64: string, options?: {
  langs?: string[];
  device?: string;
}): Promise<{ 
  text: string; 
  confidence: number;
  lines?: any[];
  lineCount?: number;
}>
```

## 解决方案

### 方案 1: 手动下载模型 (推荐)

1. **从 HuggingFace 镜像下载**:
   ```bash
   # 下载 text_detection 模型
   wget https://hf-mirror.com/datalab-to/text_detection/resolve/main/2025_05_07/model.safetensors
   
   # 下载其他配置文件
   wget https://hf-mirror.com/datalab-to/text_detection/resolve/main/2025_05_07/config.json
   wget https://hf-mirror.com/datalab-to/text_detection/resolve/main/2025_05_07/preprocessor_config.json
   ```

2. **放置到缓存目录**:
   ```
   C:\Users\74090\AppData\Local\datalab\datalab\Cache\models\text_detection\2025_05_07\
   ```

3. **重复下载 text_recognition 模型**

4. **在配置中启用 OCR**:
   ```typescript
   ocr: {
     ...
     enabled: true, // 启用
   }
   ```

### 方案 2: 等待 Surya 修复

跟踪 issue: https://github.com/VikParuchuri/surya/issues

### 方案 3: 替换 OCR 引擎

**EasyOCR** (推荐):
```bash
pip install easyocr
```

**特点**:
- ✅ 模型下载稳定
- ✅ 支持 80+ 语言
- ✅ GPU 加速
- ✅ 中英文混合识别准确

**PaddleOCR**:
```bash
pip install paddlepaddle-gpu
pip install paddleocr
```

**Tesseract**:
```bash
choco install tesseract
pip install pytesseract
```

## 测试验证

### 1. 清理缓存
```powershell
Remove-Item -Recurse -Force "C:\Users\74090\AppData\Local\datalab"
```

### 2. 测试 OCR 脚本
```bash
# 如果模型已下载
C:\Users\74090\Miniconda3\python.exe backend\scripts\surya_ocr_wrapper.py testresources\OCRtest.png --device cuda --langs zh,en
```

### 3. 集成测试
```bash
# 在配置中启用 OCR
npm run test:integration
```

## GUI 替代方案

**Surya GUI** (已可用):
```bash
surya_gui
# 浏览器访问: http://localhost:8501
```

**特点**:
- ✅ GUI 模式不受模型下载 bug 影响
- ✅ 可视化界面
- ✅ 批量处理
- ✅ 结果导出

## 性能预期

基于 Surya 官方 benchmark (如果模型下载成功):

| 指标 | 预期性能 |
|------|---------|
| **加载时间** | 10-30s (首次) |
| **检测速度** | 0.5-2s/image |
| **识别速度** | 1-3s/image |
| **准确率** | 90%+ (中英文) |
| **设备** | CUDA GPU (RTX 5080) |

## 下一步

1. **尝试手动下载模型** (如有需要)
2. **或切换到 EasyOCR/PaddleOCR**
3. **或等待 Surya 修复 bug**
4. **优先完成其他服务测试**

---

**更新时间**: 2025-11-12  
**状态**: 代码已集成,等待模型下载解决方案  
**优先级**: P2 (TTS/ASR/LLM 优先)
