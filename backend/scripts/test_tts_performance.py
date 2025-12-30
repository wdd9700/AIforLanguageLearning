#!/usr/bin/env python
"""Moved

该性能测试脚本已迁移到 `backend/scripts/obsolete/`，以避免被误当作主线入口。

当前工程 TTS 主线为 XTTS v2；如需验证主线 TTS，请使用：
- `backend/scripts/test_all_services.py`
"""

import sys


def main() -> int:
    print(
        "This script has been moved to backend/scripts/obsolete/.\n"
        "Use backend/scripts/test_all_services.py to test the primary TTS path."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
