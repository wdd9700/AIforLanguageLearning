/**
 * @fileoverview 数据库备份管理器 (Backup Manager)
 * @description
 * 该文件负责 SQLite 数据库文件的备份与恢复管理，确保数据安全。
 * 
 * 主要功能：
 * 1. 自动备份：支持定时任务（默认每 24 小时）自动备份数据库
 * 2. 手动备份：提供 API 供管理员手动触发备份
 * 3. 备份恢复：支持从指定的备份文件恢复数据库（恢复前会自动创建安全备份）
 * 4. 自动清理：实施保留策略（默认保留最近 10 个备份），自动删除旧文件以节省空间
 * 5. 列表查询：按时间倒序列出所有可用备份
 * 
 * 实现细节：
 * - 使用文件系统复制 (fs.copyFile) 实现物理备份
 * - 采用单例模式 (Singleton) 确保全局唯一
 * 
 * 待改进项：
 * - [ ] 支持增量备份 (Incremental Backup) 以减少存储占用
 * - [ ] 增加备份文件加密功能
 * - [ ] 移除硬编码的数据库路径，统一从配置文件加载
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import * as fs from 'fs';
import * as path from 'path';
import { config } from '../config/env';
import { createLogger } from '../utils/logger';

const logger = createLogger('BackupManager');

export class BackupManager {
  private static instance: BackupManager;
  private dbPath: string;
  private backupDir: string;
  private backupInterval: NodeJS.Timeout | null = null;

  private constructor() {
    // 数据库文件路径 (假设在 data/app.db)
    // TODO: 应该从 config 中读取数据库路径
    this.dbPath = path.resolve(__dirname, '../../data/app.db');
    this.backupDir = path.resolve(__dirname, '../../data/backups');
    this.init();
  }

  /**
   * 获取 BackupManager 单例
   */
  public static getInstance(): BackupManager {
    if (!BackupManager.instance) {
      BackupManager.instance = new BackupManager();
    }
    return BackupManager.instance;
  }

  /**
   * 初始化备份目录和定时任务
   */
  private init(): void {
    if (!fs.existsSync(this.backupDir)) {
      fs.mkdirSync(this.backupDir, { recursive: true });
    }
    // 启动自动备份 (默认每 24 小时)
    this.startAutoBackup(24 * 60 * 60 * 1000);
  }

  /**
   * 启动自动备份定时任务
   * @param intervalMs 备份间隔 (毫秒)
   */
  public startAutoBackup(intervalMs: number): void {
    if (this.backupInterval) {
      clearInterval(this.backupInterval);
    }
    this.backupInterval = setInterval(() => {
      this.createBackup('auto');
    }, intervalMs);
    logger.info({ intervalMs }, 'Auto-backup scheduled');
  }

  /**
   * 创建数据库备份
   * @param type 备份类型: 'auto' (自动) 或 'manual' (手动)
   * @returns 备份文件名
   */
  public async createBackup(type: 'auto' | 'manual' = 'manual'): Promise<string> {
    try {
      if (!fs.existsSync(this.dbPath)) {
        throw new Error('Database file not found');
      }

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `backup_${type}_${timestamp}.db`;
      const destPath = path.join(this.backupDir, filename);

      // 使用 copyFile 进行简单备份 (SQLite 是基于文件的)
      // 注意: 在高并发生产环境中，建议使用 SQLite 的 VACUUM INTO 或备份 API 以避免锁问题
      await fs.promises.copyFile(this.dbPath, destPath);

      logger.info({ type, filename }, 'Backup created successfully');
      
      // 清理旧备份
      this.cleanupOldBackups();

      return filename;
    } catch (error: any) {
      logger.error({ error: error.message }, 'Backup failed');
      throw error;
    }
  }

  /**
   * 列出所有备份文件
   * 按创建时间倒序排列 (最新的在最前)
   */
  public listBackups(): any[] {
    try {
      return fs.readdirSync(this.backupDir)
        .filter(f => f.endsWith('.db'))
        .map(f => {
            const stats = fs.statSync(path.join(this.backupDir, f));
            return {
                filename: f,
                size: stats.size,
                created: stats.mtime
            };
        })
        .sort((a, b) => b.created.getTime() - a.created.getTime()); // Newest first
    } catch (error) {
      return [];
    }
  }

  /**
   * 从备份文件恢复数据库
   * @param filename 备份文件名
   */
  public async restoreBackup(filename: string): Promise<void> {
    const backupPath = path.join(this.backupDir, filename);
    if (!fs.existsSync(backupPath)) {
      throw new Error('Backup file not found');
    }

    // 在恢复前创建一个安全备份 (Safety Backup)
    await this.createBackup('manual');

    try {
      // 停止数据库连接 (需要应用重启或关闭 DB 连接)
      // 目前直接覆盖文件。在生产环境中，这需要进入维护模式。
      await fs.promises.copyFile(backupPath, this.dbPath);
      logger.info({ filename }, 'Database restored successfully');
    } catch (error: any) {
      logger.error({ error: error.message }, 'Restore failed');
      throw error;
    }
  }

  /**
   * 清理旧备份文件
   * 默认保留最近 10 个备份
   */
  private cleanupOldBackups(): void {
    try {
      const backups = this.listBackups();
      const maxBackups = 10; // 保留最近 10 个

      if (backups.length > maxBackups) {
        const toDelete = backups.slice(maxBackups);
        toDelete.forEach(file => {
          fs.unlinkSync(path.join(this.backupDir, file.filename));
        });
        logger.info({ count: toDelete.length }, 'Cleaned up old backups');
      }
    } catch (error) {
      logger.error({ error }, 'Backup cleanup failed');
    }
  }
}
