/**
 * @fileoverview TTS 服务 (Text-to-Speech Service)
 * 
 * 负责语音合成功能，支持流式合成。
 * 底层调用 Python 脚本 (基于 XTTS) 进行推理。
 * 
 * 主要功能：
 * 1. 进程管理：管理长期运行的 Python TTS 子进程
 * 2. 语音合成 (Synthesize)：发送文本到子进程，接收并拼接音频数据流
 * 3. 兼容接口 (Invoke)：提供统一的单次调用接口
 * 4. 错误处理：处理进程异常、超时和 JSON 解析错误
 * 
 * 待改进项：
 * - [ ] 支持更多合成选项 (如语速、音色选择)
 * - [ ] 优化进程启动和就绪检测机制 (目前使用固定延时)
 * - [ ] 移除硬编码的脚本路径和 Prompt 音频路径，统一从配置文件加载
 * - [ ] 修复配置对象中的 `any` 类型断言，完善类型定义
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { BaseService } from './base.service';
import { config } from '../config/env';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

export class TTSService extends BaseService {
  private process: ChildProcess | null = null;
  private pythonPath: string;
  private scriptPath: string;

  constructor() {
    super('tts');
    this.pythonPath = config.services.tts.pythonPath;
    this.scriptPath = config.services.tts.scriptPath;
  }

  /**
   * 初始化 TTS 服务
   * 检查 Python 环境和脚本文件
   */
  async initialize(): Promise<void> {
    if (!fs.existsSync(this.pythonPath)) {
      this.updateStatus('error', `Python executable not found at ${this.pythonPath}`);
      return;
    }
    if (!fs.existsSync(this.scriptPath)) {
      this.updateStatus('error', `TTS script not found at ${this.scriptPath}`);
      return;
    }
    this.logger.info('TTS Service initialized');
    this.updateStatus('stopped');
  }

  async shutdown(): Promise<void> {
    this.stopProcess();
  }

  async healthCheck(): Promise<boolean> {
    if (this.status.status === 'error') {
      return false;
    }
    if (this.status.status === 'running') {
      if (!this.process || this.process.killed || this.process.exitCode !== null) {
        this.updateStatus('error', 'TTS process died unexpectedly');
        return false;
      }
      return true;
    }
    // stopped or initializing
    return fs.existsSync(this.pythonPath) && fs.existsSync(this.scriptPath);
  }

  /**
   * 启动 TTS 进程
   * 进程通过标准输入接收 JSON 请求，标准输出返回 JSON 格式的音频数据
   */
  public start(): ChildProcess {
    if (this.process && !this.process.killed) {
      return this.process;
    }

    this.logger.info('Starting TTS Process...');

    try {
      const env = {
        ...process.env,
        XTTS_PROMPT_WAV: config.services.tts.promptAudioPath,
        PYTHONIOENCODING: 'utf-8'
      };

      this.process = spawn(this.pythonPath, [this.scriptPath], {
        cwd: path.dirname(this.scriptPath),
        stdio: ['pipe', 'pipe', 'pipe'],
        env
      });

      this.updateStatus('running');

      this.process.stderr?.on('data', (data) => {
        this.logger.warn(`[TTS STDERR] ${data.toString().trim()}`);
      });

      this.process.on('exit', (code) => {
        this.logger.warn({ code }, 'TTS Process exited');
        this.process = null;
        this.updateStatus('stopped', `Process exited with code ${code}`);
      });
      
      return this.process;

    } catch (error: any) {
      this.logger.error({ error: error.message }, 'Failed to spawn TTS process');
      this.updateStatus('error', error.message);
      throw error;
    }
  }

  public stopProcess(): void {
    if (this.process) {
      this.process.kill();
      this.process = null;
      this.updateStatus('stopped');
    }
  }

  /**
   * 合成语音
   * 发送合成请求到 Python 进程，并等待返回完整的音频数据
   * @param text 待合成的文本
   */
  public async synthesize(text: string): Promise<Buffer> {
    // 自动启动
    if (!this.process) {
      this.start();
      // 等待启动 (简单处理，实际应监听 Ready 信号)
      await new Promise(resolve => setTimeout(resolve, 2000));
    }

    // Capture process locally to satisfy TS and ensure consistency
    const proc = this.process;
    if (!proc || !proc.stdin || !proc.stdout) {
      throw new Error('TTS Service not ready');
    }

    return new Promise((resolve, reject) => {
      const chunks: Buffer[] = [];
      let isResolved = false;
      let buffer = '';
      
      const timeout = setTimeout(() => {
        if (!isResolved) {
          cleanup();
          reject(new Error("TTS request timed out"));
        }
      }, 30000);

      const dataListener = (data: Buffer) => {
        buffer += data.toString();
        let boundary = buffer.indexOf('\n');
        
        while (boundary !== -1) {
          const line = buffer.substring(0, boundary).trim();
          buffer = buffer.substring(boundary + 1);
          boundary = buffer.indexOf('\n');

          if (!line) continue;
          
          try {
            const msg = JSON.parse(line);
            if (msg.type === 'audio') {
              chunks.push(Buffer.from(msg.data, 'base64'));
            } else if (msg.type === 'done') {
              cleanup();
              isResolved = true;
              resolve(Buffer.concat(chunks));
            } else if (msg.type === 'error') {
              cleanup();
              isResolved = true;
              reject(new Error(msg.error ?? msg.message ?? 'TTS error'));
            }
          } catch (e) {
            console.error('[TTS Service] JSON Parse Error:', e, 'Line:', line);
            // Continue processing other lines, don't crash the whole request for one bad line unless it's critical
          }
        }
      };

      const cleanup = () => {
        clearTimeout(timeout);
        proc.stdout?.removeListener('data', dataListener);
      };

      proc.stdout!.on('data', dataListener);

      // 发送请求
      const ttsConfig = config.services.tts as any;
      const promptWav = ttsConfig.promptAudioPath || "e:\\projects\\AiforForiegnLanguageLearning\\testresources\\TTSpromptAudio.wav";
      const req = { text, language: 'zh' };
      
      try {
        proc.stdin!.write(JSON.stringify(req) + "\n");
      } catch (e) {
        cleanup();
        reject(e);
      }
    });
  }

  /**
   * 单次调用 TTS (兼容接口)
   */
  async invoke(text: string, options?: {
    voice?: string;
    speed?: number;
  }): Promise<{ audio: Buffer; format: string; duration?: number }> {
    // 简单实现：调用 synthesize
    // TODO: 支持 options
    const audio = await this.synthesize(text);
    return {
      audio,
      format: 'wav', // 假设是 wav
    };
  }
}
