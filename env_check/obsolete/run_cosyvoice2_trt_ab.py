#!/usr/bin/env python3
"""
TRT A/B 对比小工具

用途：
- 以相同输入分别在 "关闭TRT" 和 "开启TRT" 模式下运行一次零样本流式合成脚本，解析 TTFT 并记录到 CSV。
- 默认以环境变量方式切换（例如 COSY_LOAD_TRT=0/1），对子进程透明，不依赖内部 API。

前置：
- 需要已有可运行的零样本脚本（例如 env_check/run_cosyvoice2_zero_shot.py），且其 stdout 中包含形如 "TTFT: 1.234 s" 的输出。

用法示例：
  python -m env_check.run_cosyvoice2_trt_ab \
    --cmd "python -m env_check.run_cosyvoice2_zero_shot --text '你好世界' --prompt_wav env_check/zero_shot_prompt.wav --use_flow_cache --use_fp16" \
    --trt-env COSY_LOAD_TRT \
    --csv out_trt_ab.csv

说明：
- 本脚本不会直接导入 CosyVoice2，仅负责 A/B 调度与结果解析，方便替换被测脚本。
- 若你的零样本脚本提供 --load_trt 标志，可将其直接写入 --cmd；或用 --trt-env 指定环境变量名。
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import time
from typing import Dict, Tuple, Optional


TTFT_RE = re.compile(r"TTFT\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*s", re.IGNORECASE)


def run_once(label: str, base_cmd: str, extra_env: Dict[str, str], timeout_s: Optional[float] = None) -> Tuple[int, float, Optional[float], str]:
    """
    以给定环境变量运行一次命令，返回：
    - returncode: 进程退出码
    - wall_time_s: 总耗时（秒）
    - ttft_s: 解析到的 TTFT（秒），解析失败为 None
    - stdout_tail: 标准输出末尾若干行（便于排错）
    """
    env = os.environ.copy()
    env.update(extra_env)

    # 兼容用户传入字符串命令
    cmd_list = base_cmd if isinstance(base_cmd, list) else shlex.split(base_cmd)

    t0 = time.perf_counter()
    proc = subprocess.Popen(
        cmd_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    lines = []
    ttft_s: Optional[float] = None
    try:
        assert proc.stdout is not None
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            sys.stdout.write(f"[{label}] "+line)
            lines.append(line.rstrip())
            m = TTFT_RE.search(line)
            if m:
                try:
                    ttft_s = float(m.group(1))
                except Exception:
                    pass
            # timeout guard
            if timeout_s is not None and (time.perf_counter() - t0) > timeout_s:
                try:
                    proc.terminate()
                except Exception:
                    pass
                break
    finally:
        try:
            returncode = proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
            returncode = -9

    wall = time.perf_counter() - t0
    tail = "\n".join(lines[-20:])
    return returncode, wall, ttft_s, tail


def main():
    parser = argparse.ArgumentParser(description="CosyVoice2 TRT A/B 对比")
    parser.add_argument("--cmd", required=True, help="被测命令（字符串），例如: \"python -m env_check.run_cosyvoice2_zero_shot --text '你好' --prompt_wav env_check/zero_shot_prompt.wav --use_flow_cache --use_fp16\"")
    parser.add_argument("--trt-env", default="COSY_LOAD_TRT", help="用于控制是否启用 TRT 的环境变量名（默认 COSY_LOAD_TRT，0/1 切换）")
    parser.add_argument("--csv", default="trt_ab_results.csv", help="结果输出 CSV 路径")
    parser.add_argument("--timeout", type=float, default=None, help="单次运行最大墙钟时长（秒）。超时将终止子进程并记录已产生的日志。")
    parser.add_argument("--env", action="append", default=[], help="额外传入子进程环境变量（格式 KEY=VAL，可多次提供）")
    parser.add_argument("--warmup", type=int, default=0, help="在 A/B 之前的预热次数（不记录结果）")
    args = parser.parse_args()

    base_cmd = args.cmd

    # 聚合额外环境
    extra_env_base: Dict[str, str] = {}
    for kv in args.env:
        if "=" in kv:
            k, v = kv.split("=", 1)
            extra_env_base[k] = v

    # 预热（不计分）
    for i in range(args.warmup):
        print(f"[warmup {i+1}] running with {args.trt_env}=0 …")
        env_warm = dict(extra_env_base)
        env_warm[args.trt_env] = "0"
        run_once("warmup", base_cmd, env_warm, timeout_s=args.timeout)

    print("\n=== Running A (TRT=0) ===")
    env_a = dict(extra_env_base)
    env_a[args.trt_env] = "0"
    rc_a, wall_a, ttft_a, tail_a = run_once("A", base_cmd, env_a, timeout_s=args.timeout)

    print("\n=== Running B (TRT=1) ===")
    env_b = dict(extra_env_base)
    env_b[args.trt_env] = "1"
    rc_b, wall_b, ttft_b, tail_b = run_once("B", base_cmd, env_b, timeout_s=args.timeout)

    # 写 CSV
    os.makedirs(os.path.dirname(args.csv) or ".", exist_ok=True)
    with open(args.csv, "w", encoding="utf-8") as f:
        f.write("label,returncode,wall_time_s,ttft_s\n")
        f.write(f"A,{rc_a},{wall_a:.3f},{'' if ttft_a is None else f'{ttft_a:.3f}'}\n")
        f.write(f"B,{rc_b},{wall_b:.3f},{'' if ttft_b is None else f'{ttft_b:.3f}'}\n")

    print("\n=== Summary ===")
    print(f"A (TRT=0): rc={rc_a}, wall={wall_a:.3f}s, ttft={'NA' if ttft_a is None else f'{ttft_a:.3f}s'}")
    print(f"B (TRT=1): rc={rc_b}, wall={wall_b:.3f}s, ttft={'NA' if ttft_b is None else f'{ttft_b:.3f}s'}")
    print(f"CSV saved to: {args.csv}")

    # 失败时附带尾部日志提示
    if rc_a != 0:
        print("\n[A] tail:\n" + tail_a)
    if rc_b != 0:
        print("\n[B] tail:\n" + tail_b)

    # 以 B 的退出码为主（若 B 失败则整体失败）
    sys.exit(rc_b if rc_b != 0 else rc_a)


if __name__ == "__main__":
    main()
