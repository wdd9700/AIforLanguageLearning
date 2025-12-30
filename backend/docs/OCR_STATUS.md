# OCR 服务集成说明（PaddleOCR）

## 状态: ✅ 主线启用（PaddleOCR）

OCR 服务当前使用 PaddleOCR，通过 Python 包装脚本输出 JSON，由 Node 后端以子进程方式调用。

历史方案已归档：`backend/docs/obsolete/OCR_STATUS_OBSOLETE.md`

## 关键实现

- Python 包装脚本：`backend/scripts/paddleocr_v3_wrapper.py`
- Node 服务实现：`backend/src/services/ocr.service.ts`
- 默认脚本路径配置：`backend/src/config/env.ts`

## 本地验证

1) 单图命令行

```powershell
python .\backend\scripts\paddleocr_v3_wrapper.py .\testresources\OCRtest.png japan true
```

2) 一键联测（推荐）

```powershell
python .\backend\scripts\test_all_services.py
```

---

**更新时间**: 2025-12-27
