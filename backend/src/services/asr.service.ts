/**
 * @fileoverview ASR 服务 (Automatic Speech Recognition Service)
 * 
 * 负责语音转文字功能，支持流式 (Streaming) 和非流式 (Single-shot) 两种模式。
 * 底层调用 Python 脚本 (基于 Faster-Whisper) 进行推理。
 * 
 * 主要功能：
 * 1. 流式识别 (Streaming)：管理长期运行的 Python 子进程，通过标准输入/输出进行实时语音识别
 * 2. 单次识别 (Invoke)：处理单次语音文件转写请求，使用临时文件进行数据交换
 * 3. 进程管理：负责 Python 进程的启动、监控、重启和资源释放
 * 4. 错误处理：捕获子进程异常和执行错误
 * 
 * 待改进项：
 * - [ ] 优化临时文件管理，考虑使用内存管道替代文件交换以提升性能
 * - [ ] 增加对 VAD (Voice Activity Detection) 的支持，减少静音片段的无效识别
 * - [ ] 移除硬编码的脚本路径，统一从配置文件加载
 * - [ ] 修复配置对象中的 `any` 类型断言，完善类型定义
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { BaseService } from './base.service';
import { config } from '../config/env';
import { spawn, ChildProcess, execFile } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

export interface ASRResponse {
  text: string;
  segments?: any[];
  language?: string;
  duration?: number;
}

export class ASRService extends BaseService {
  private process: ChildProcess | null = null;
  private pythonPath: string;
  private streamingScriptPath: string;
  private wrapperScriptPath: string;

  constructor() {
    super('asr');
    this.pythonPath = config.services.asr.pythonPath || config.pythonPath;
    this.streamingScriptPath = path.resolve(__dirname, '../../../env_check/run_streaming_asr.py');
    this.wrapperScriptPath = (config.services.asr as any).scriptPath;
  }

  /**
   * 初始化 ASR 服务
   * 检查 Python 环境和必要的脚本文件是否存在
   */
  async initialize(): Promise<void> {
    // 检查 Python 环境
    if (!fs.existsSync(this.pythonPath)) {
      this.updateStatus('error', `Python executable not found at ${this.pythonPath}`);
      return;
    }
    
    if (!fs.existsSync(this.streamingScriptPath)) {
      this.logger.warn({ script: this.streamingScriptPath }, 'Streaming ASR script not found');
    }
    if (!fs.existsSync(this.wrapperScriptPath)) {
      this.logger.warn({ script: this.wrapperScriptPath }, 'Wrapper ASR script not found');
    }

    this.logger.info('ASR Service initialized (Process will start on demand)');
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
        this.updateStatus('error', 'ASR process died unexpectedly');
        return false;
      }
      return true;
    }
    return fs.existsSync(this.pythonPath);
  }

  /**
   * 启动流式 ASR 进程
   * 该进程会长期运行，通过标准输入接收音频流，标准输出返回识别结果
   */
  public start(): ChildProcess {
    if (this.process && !this.process.killed) {
      return this.process;
    }

    this.logger.info({ 
      script: this.streamingScriptPath, 
      python: this.pythonPath 
    }, 'Starting Streaming ASR Process...');

    try {
      this.process = spawn(this.pythonPath, [this.streamingScriptPath], {
        cwd: path.dirname(this.streamingScriptPath),
        stdio: ['pipe', 'pipe', 'pipe'],
        env: {
          ...process.env,
          ASR_MODEL_SIZE: config.services.asr.modelSize || 'medium',
          ASR_DEVICE: (config.services.asr as any).device || 'cuda',
          ASR_COMPUTE_TYPE: config.services.asr.computeType || 'float16'
        }
      });

      this.updateStatus('running');

      this.process.stderr?.on('data', (data) => {
        const msg = data.toString().trim();
        if (msg.includes('Loading Whisper') || msg.includes('Model loaded')) {
          this.logger.info(`[ASR] ${msg}`);
        } else {
          this.logger.warn(`[ASR STDERR] ${msg}`);
        }
      });

      this.process.on('exit', (code) => {
        this.logger.warn({ code }, 'ASR Process exited');
        this.process = null;
        this.updateStatus('stopped', `Process exited with code ${code}`);
      });
      
      return this.process;

    } catch (error: any) {
      this.logger.error({ error: error.message }, 'Failed to spawn ASR process');
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
   * 获取进程输入流 (用于写入音频数据)
   */
  public getInputStream() {
    return this.process?.stdin;
  }

  /**
   * 单次调用 ASR (非流式)
   * 将音频 Buffer 写入临时文件，调用 Python 脚本进行转写，然后读取结果
   * @param audioBuffer 音频数据
   * @param options 配置选项 (语言, 模型)
   */
  async invoke(audioBuffer: Buffer, options?: {
    language?: string;
    model?: string;
  }): Promise<ASRResponse> {
    this.logger.debug({ options }, 'Invoking ASR service (Single-shot)');
    
    // 创建临时文件
    const tempDir = path.join(__dirname, '../../temp');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }
    
    const timestamp = Date.now();
    const inputPath = path.join(tempDir, `asr_input_${timestamp}.wav`);
    
    try {
      await fs.promises.writeFile(inputPath, audioBuffer);
      
      const asrConfig = config.services.asr;
      const model = options?.model || asrConfig.modelSize;
      const language = options?.language || 'auto';
      
      const args = [
        this.wrapperScriptPath,
        inputPath,
        '--model', model,
        '--compute-type', asrConfig.computeType,
        '--cpu-threads', (asrConfig.cpuThreads || 4).toString(),
      ];
      
      if (language && language !== 'auto') {
        args.push('--language', language);
      }
      
      this.logger.debug({ command: `${this.pythonPath} ${args.join(' ')}`, timeout: asrConfig.timeout }, 'Executing Faster-Whisper Wrapper');
      
      let stdout, stderr;
      try {
        const result = await execFileAsync(this.pythonPath, args, {
            timeout: asrConfig.timeout || 30000,
            maxBuffer: 10 * 1024 * 1024,
            env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
        });
        stdout = result.stdout;
        stderr = result.stderr;
      } catch (execError: any) {
        this.logger.error({ error: execError, stderr: execError.stderr, stdout: execError.stdout }, 'ASR Execution Failed');
        throw new Error(`ASR Execution Failed: ${execError.message}`);
      }
      
      if (stderr) {
        // this.logger.debug({ stderr }, 'Faster-Whisper stderr');
      }
      
      // Robust JSON parsing: find the first '{' and last '}'
      const jsonStart = stdout.indexOf('{');
      const jsonEnd = stdout.lastIndexOf('}');
      
      if (jsonStart === -1 || jsonEnd === -1) {
          throw new Error('ASR Output is not valid JSON: ' + stdout);
      }
      
      const jsonStr = stdout.substring(jsonStart, jsonEnd + 1);
      const result = JSON.parse(jsonStr);
      
      if (!result.success) {
        throw new Error(result.error || 'ASR failed');
      }
      
      return {
        text: result.text,
        segments: result.segments,
        language: result.language,
        duration: result.duration
      };
      
    } catch (error: any) {
      this.logger.error({ error: error.message }, 'ASR invoke failed');
      throw error;
    } finally {
      try {
        if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
      } catch {}
    }
  }
}
