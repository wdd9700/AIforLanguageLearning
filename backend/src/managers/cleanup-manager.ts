/**
 * @fileoverview 临时文件清理管理器 (Cleanup Manager)
 * 
 * 该文件负责维护系统的磁盘卫生，定期清理过期的临时文件。
 * 
 * 主要功能：
 * 1. 目录扫描：自动扫描预定义的临时目录 (如 temp/, assets/temp/)
 * 2. 过期判定：基于文件的最后修改时间 (mtime) 和配置的生命周期 (maxAge) 判定文件是否过期
 * 3. 安全删除：批量删除过期文件，并统计成功和失败的数量
 * 
 * 适用场景：
 * - 清理 TTS 生成的临时音频文件
 * - 清理上传的临时图片或文档
 * - 清理中间处理产物
 * 
 * 待改进项：
 * - [ ] 增加基于磁盘使用率的清理策略 (如本应用缓存内容磁盘占用 > 10G 时强制清理)
 * - [ ] 支持按文件类型过滤清理
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import * as fs from 'fs';
import * as path from 'path';
import { createLogger } from '../utils/logger';

const logger = createLogger('CleanupManager');

export class CleanupManager {
  private static instance: CleanupManager;
  private tempDirs: string[];

  private constructor() {
    // 定义需要清理的临时目录列表
    this.tempDirs = [
      path.resolve(__dirname, '../../temp'),
      path.resolve(__dirname, '../../assets/temp')
    ];
  }

  /**
   * 获取 CleanupManager 单例
   */
  public static getInstance(): CleanupManager {
    if (!CleanupManager.instance) {
      CleanupManager.instance = new CleanupManager();
    }
    return CleanupManager.instance;
  }

  /**
   * 清理临时文件
   * 删除修改时间超过 maxAgeMs 的文件
   * @param maxAgeMs 文件最大保留时间 (毫秒)，默认 1 小时
   * @returns 清理结果 { deleted: 删除文件数, errors: 错误数 }
   */
  public async cleanTempFiles(maxAgeMs: number = 3600000): Promise<{ deleted: number; errors: number }> {
    let deleted = 0;
    let errors = 0;
    const now = Date.now();

    for (const dir of this.tempDirs) {
      if (!fs.existsSync(dir)) continue;

      try {
        const files = await fs.promises.readdir(dir);
        for (const file of files) {
          const filePath = path.join(dir, file);
          try {
            const stats = await fs.promises.stat(filePath);
            // 如果文件修改时间早于 (当前时间 - 最大保留时间)，则删除
            if (now - stats.mtimeMs > maxAgeMs) {
              await fs.promises.unlink(filePath);
              deleted++;
            }
          } catch (e) {
            errors++;
          }
        }
      } catch (e) {
        logger.error({ dir, error: e }, 'Failed to read temp directory');
      }
    }

    logger.info({ deleted, errors }, 'Cleanup completed');
    return { deleted, errors };
  }
}
