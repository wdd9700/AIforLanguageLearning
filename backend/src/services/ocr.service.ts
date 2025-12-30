/**
 * @fileoverview OCR 服务 (Optical Character Recognition Service)
 * 
 * 负责图像文字识别功能。
 * 底层调用 Python 脚本 (基于 PaddleOCR) 进行推理。
 * 
 * 主要功能：
 * 1. 服务初始化：检查 PaddleOCR 环境配置和脚本状态
 * 2. 图像识别 (Invoke)：接收 Base64 图片，调用 Python 脚本进行 OCR 处理
 * 3. 结果解析：解析 PaddleOCR 返回的 JSON 数据，提取文本、置信度和坐标信息
 * 4. 资源管理：自动清理临时图片文件，处理进程超时
 * 
 * 待改进项：
 * - [ ] 优化临时文件处理，支持内存流传输
 * - [ ] 增加对多语言混合识别的配置支持
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { BaseService } from './base.service';
import { config } from '../config/env';
import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

export interface OCRResponse {
  text: string;
  confidence: number | null;
  lines?: any[];
  lineCount?: number;
}

export interface OCROptions {
  langs?: string;
  useAngleCls?: boolean;
}

export class OCRService extends BaseService {
  constructor() {
    super('ocr');
  }

  /**
   * 初始化 OCR 服务
   * 检查配置是否启用以及脚本是否存在
   */
  async initialize(): Promise<void> {
    if (!config.services.ocr.enabled) {
      this.logger.info('OCR service is disabled in config');
      this.updateStatus('stopped', 'Disabled in config');
      return;
    }

    const ocrCfg: any = config.services.ocr;
    const scriptPath = ocrCfg.scriptPath;
    
    if (!scriptPath || !fs.existsSync(scriptPath)) {
      this.logger.error({ scriptPath }, 'PaddleOCR script not found');
      this.updateStatus('error', 'Script not found');
      return;
    }

    this.logger.info({ scriptPath }, 'OCR Service initialized (PaddleOCR)');
    this.updateStatus('running');
  }

  async shutdown(): Promise<void> {
    this.updateStatus('stopped');
  }

  async healthCheck(): Promise<boolean> {
    if (!config.services.ocr.enabled) return true;
    const ocrCfg: any = config.services.ocr;
    const exists = fs.existsSync(ocrCfg.scriptPath);
    if (!exists) {
      this.updateStatus('error', 'Script missing');
    }
    return exists;
  }

  /**
   * 调用 OCR 识别
   * 将 Base64 图片保存为临时文件，调用 Python 脚本进行识别
   * @param imageBase64 图片 Base64 编码
   * @param options 识别选项 (语言, 角度分类)
   */
  async invoke(imageBase64: string, options?: OCROptions): Promise<OCRResponse> {
    if (this.status.status !== 'running') {
      throw new Error('OCR service is not running');
    }

    const ocrCfg: any = config.services.ocr;
    const langs = options?.langs || ocrCfg.langs || 'japan';
    const useAngleCls = (options?.useAngleCls !== undefined ? options.useAngleCls : ocrCfg.useAngleCls) ?? false;

    // 创建临时文件
    const tempDir = path.join(__dirname, '../../temp');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const timestamp = Date.now();
    const tempImagePath = path.join(tempDir, `ocr_input_${timestamp}.png`);
    const imageBuffer = Buffer.from(imageBase64, 'base64');
    fs.writeFileSync(tempImagePath, imageBuffer);

    const args = [
      ocrCfg.scriptPath,
      tempImagePath,
      langs,
      useAngleCls.toString()
    ];

    this.logger.debug({ 
      pythonPath: ocrCfg.pythonPath,
      scriptPath: ocrCfg.scriptPath,
      tempImagePath,
      langs,
      useAngleCls,
      timeout: ocrCfg.timeout 
    }, 'Spawning PaddleOCR wrapper');

    return new Promise((resolve, reject) => {
      const child = spawn(ocrCfg.pythonPath, args, {
        env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
        stdio: ['ignore', 'pipe', 'pipe']
      });

      let stdoutData = '';
      let stderrData = '';

      const timeoutMs = ocrCfg.timeout && ocrCfg.timeout > 0 ? ocrCfg.timeout : 60000;
      const timeoutHandle = setTimeout(() => {
        this.logger.warn({ timeoutMs }, 'OCR process timeout reached');
        try { child.kill('SIGTERM'); } catch {}
        try { fs.unlinkSync(tempImagePath); } catch {}
        reject(new Error(`OCR process exceeded timeout ${timeoutMs} ms`));
      }, timeoutMs);

      child.stdout.on('data', (chunk: Buffer) => {
        stdoutData += chunk.toString('utf-8');
      });

      child.stderr.on('data', (chunk: Buffer) => {
        stderrData += chunk.toString('utf-8');
      });

      child.on('error', (err) => {
        clearTimeout(timeoutHandle);
        try { fs.unlinkSync(tempImagePath); } catch {}
        this.logger.error({ err }, 'PaddleOCR spawn error');
        reject(new Error(`OCR process spawn failed: ${err.message}`));
      });

      child.on('close', (code) => {
        clearTimeout(timeoutHandle);
        
        // 清理临时文件
        try {
          fs.unlinkSync(tempImagePath);
        } catch {}

        if (code !== 0) {
          this.logger.error({ code, stderr: stderrData }, 'PaddleOCR exited with error');
          return reject(new Error(`PaddleOCR exited with code ${code}: ${stderrData}`));
        }

        try {
          // Robust JSON parsing: find the first '{' and last '}'
          // This handles cases where PaddleOCR prints logs before/after the JSON output
          const jsonStart = stdoutData.indexOf('{');
          const jsonEnd = stdoutData.lastIndexOf('}');
          
          if (jsonStart === -1 || jsonEnd === -1) {
             throw new Error('No JSON found in OCR output');
          }
          
          const jsonStr = stdoutData.substring(jsonStart, jsonEnd + 1);
          const result = JSON.parse(jsonStr);

          if (!result.success) {
            return reject(new Error(`OCR failed: ${result.error || 'Unknown error'}`));
          }

          const lines = result.results || [];
          const text = lines.map((line: any) => line.text).join('\n');
          const lineCount = result.count || lines.length;

          this.logger.info({ 
            textLength: text.length, 
            lineCount,
            avgConfidence: lines.length > 0 
              ? lines.reduce((sum: number, l: any) => sum + (l.confidence || 0), 0) / lines.length 
              : null
          }, 'OCR completed successfully');

          resolve({
            text,
            confidence: lines.length > 0 
              ? lines.reduce((sum: number, l: any) => sum + (l.confidence || 0), 0) / lines.length 
              : null,
            lines,
            lineCount
          });
        } catch (e) {
          this.logger.error({ error: e, stdout: stdoutData }, 'Failed to parse OCR output');
          reject(new Error('Failed to parse OCR output'));
        }
      });
    });
  }
}
