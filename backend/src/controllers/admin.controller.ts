/**
 * @fileoverview 管理员控制器 (Admin Controller)
 * @description
 * 提供系统管理相关的 API 接口，仅限管理员访问。
 * 
 * 主要功能：
 * 1. 配置管理：获取和更新系统全局配置 (ConfigManager)。
 * 2. 服务管理：监控和控制后台服务 (ServiceManager)。
 * 3. 备份与恢复：管理数据库和配置文件的备份 (BackupManager)。
 * 4. 系统维护：执行磁盘清理和日志轮转 (CleanupManager)。
 * 5. 安全管理：密钥轮换 (KMS) 和管理员账户重置。
 * 6. 系统监控：获取服务器资源使用情况 (CPU, 内存, 磁盘)。
 */

import { Request, Response } from 'express';
import { ConfigManager } from '../managers/config-manager';
import { ServiceManager } from '../managers/service-manager';
import { BackupManager } from '../managers/backup-manager';
import { CleanupManager } from '../managers/cleanup-manager';
import { KMS } from '../security/kms';
import { UserModel } from '../models/user';
import { Database } from '../database/db';
import { createLogger } from '../utils/logger';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

const logger = createLogger('AdminController');

export class AdminController {
  private configManager: ConfigManager;
  private serviceManager: ServiceManager;
  private backupManager: BackupManager;
  private cleanupManager: CleanupManager;
  private kms: KMS;
  private userModel: UserModel;

  constructor(db: Database, serviceManager: ServiceManager) {
    this.configManager = ConfigManager.getInstance();
    this.serviceManager = serviceManager;
    this.backupManager = BackupManager.getInstance();
    this.cleanupManager = CleanupManager.getInstance();
    this.kms = KMS.getInstance();
    this.userModel = new UserModel(db);
  }

  /**
   * 获取完整系统配置
   * 
   * 返回当前生效的所有配置项，包括 LLM、ASR、TTS 等服务的参数。
   */
  public getConfig = (req: Request, res: Response) => {
    try {
      const config = this.configManager.getConfig();
      res.json({ success: true, data: config });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 更新系统配置
   * 
   * 接收新的配置对象，验证并应用更改。
   * 部分配置更改可能需要重启服务才能生效。
   */
  public updateConfig = (req: Request, res: Response) => {
    try {
      const newConfig = req.body;
      this.configManager.updateConfig(newConfig);
      res.json({ success: true, message: '配置更新成功' });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 获取所有 Prompt 模板
   * 
   * 返回系统中定义的所有提示词模板，按类别分组 (如 conversation, essay, vocabulary)。
   */
  public getPrompts = (req: Request, res: Response) => {
    try {
      const config = this.configManager.getConfig();
      res.json({ success: true, data: config.prompts });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 更新特定类别的 Prompt
   * 
   * 修改指定的提示词模板。
   * @param category - 提示词类别 (如 'conversation')
   * @param key - 提示词键名 (如 'system')
   * @param value - 新的提示词内容
   */
  public updatePrompt = (req: Request, res: Response) => {
    try {
      const { category } = req.params;
      const { key, value } = req.body;

      if (!key || value === undefined) {
        res.status(400).json({ success: false, error: '缺少键或值' });
        return;
      }

      // @ts-ignore
      this.configManager.updatePrompt(category, key, value);
      res.json({ success: true, message: `Prompt ${category}.${key} 更新成功` });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 获取服务状态和配置
   * 
   * 返回所有后台服务 (LLM, ASR, TTS, OCR) 的运行状态 (running/stopped/error) 和当前配置。
   */
  public getServices = (req: Request, res: Response) => {
    try {
      const status = this.serviceManager.getStatus();
      const config = this.configManager.getConfig();
      res.json({ 
        success: true, 
        data: {
            status,
            config: config.services
        }
      });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 列出所有备份
   * 
   * 返回备份目录下的所有备份文件列表，包含文件名、大小和创建时间。
   */
  public listBackups = (req: Request, res: Response) => {
    try {
      const backups = this.backupManager.listBackups();
      res.json({ success: true, data: backups });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 创建新备份 (手动触发)
   * 
   * 立即执行一次全量备份，包括数据库文件和配置文件。
   */
  public createBackup = async (req: Request, res: Response) => {
    try {
      const filename = await this.backupManager.createBackup('manual');
      res.json({ success: true, message: '备份创建成功', data: { filename } });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 恢复备份
   * 
   * 从指定的备份文件恢复数据库和配置。
   * 警告：此操作会覆盖当前数据，建议在恢复前先创建新的备份。
   * 恢复完成后通常需要重启服务。
   */
  public restoreBackup = async (req: Request, res: Response) => {
    try {
      const { filename } = req.body;
      if (!filename) {
        res.status(400).json({ success: false, error: '缺少文件名' });
        return;
      }
      await this.backupManager.restoreBackup(filename);
      res.json({ success: true, message: '备份恢复成功，请重启服务器以生效。' });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 获取最近的日志
   * 
   * 读取应用日志文件的最后 100 行，用于快速排查问题。
   */
  public getLogs = (req: Request, res: Response) => {
    try {
      const logPath = path.join(__dirname, '../../../logs/app.log');
      if (fs.existsSync(logPath)) {
        // 简单读取最后 100 行
        const content = fs.readFileSync(logPath, 'utf-8');
        const lines = content.split('\n').slice(-100);
        res.json({ success: true, data: lines });
      } else {
        res.json({ success: true, data: [] });
      }
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 清空日志
   * 
   * 截断应用日志文件，释放磁盘空间。
   */
  public clearLogs = (req: Request, res: Response) => {
    try {
      const logPath = path.join(__dirname, '../../../logs/app.log');
      if (fs.existsSync(logPath)) {
        fs.writeFileSync(logPath, '');
      }
      res.json({ success: true, message: '日志已清空' });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 加密文本 (工具接口)
   * 
   * 使用系统 KMS 对敏感文本进行加密。
   * 可用于生成配置文件中的加密字段。
   */
  public encryptText = (req: Request, res: Response) => {
    try {
      const { text } = req.body;
      if (!text) {
        res.status(400).json({ success: false, error: '缺少文本' });
        return;
      }
      const encrypted = this.kms.encrypt(text);
      res.json({ success: true, data: encrypted });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 获取系统资源状态
   * 
   * 返回服务器的硬件资源使用情况，包括 CPU 负载、内存使用率、运行时间等。
   * 用于前端仪表盘展示服务器健康状态。
   */
  public getSystemStats = (req: Request, res: Response) => {
    try {
      const stats = {
        platform: os.platform(),
        arch: os.arch(),
        cpus: os.cpus().length,
        totalMem: os.totalmem(),
        freeMem: os.freemem(),
        uptime: os.uptime(),
        loadAvg: os.loadavg(),
        process: {
            uptime: process.uptime(),
            memoryUsage: process.memoryUsage(),
            pid: process.pid
        }
      };
      res.json({ success: true, data: stats });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 触发临时文件清理
   * 
   * 手动触发 CleanupManager 清理过期的临时文件 (如上传的音频、生成的 TTS 文件)。
   * @param maxAgeMs - 文件保留时间 (毫秒)，超过此时间的文件将被删除。
   */
  public cleanup = async (req: Request, res: Response) => {
    try {
      const { maxAgeMs } = req.body;
      const result = await this.cleanupManager.cleanTempFiles(maxAgeMs);
      res.json({ success: true, data: result });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 列出所有用户
   * 
   * 分页获取系统中的用户列表。
   */
  public listUsers = async (req: Request, res: Response) => {
    try {
      const limit = parseInt(req.query.limit as string) || 50;
      const offset = parseInt(req.query.offset as string) || 0;
      const result = await this.userModel.findAll(limit, offset);
      res.json({ success: true, data: result });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 重置用户密码
   * 
   * 管理员强制重置指定用户的密码。
   */
  public resetUserPassword = async (req: Request, res: Response) => {
    try {
      const userId = parseInt(req.params.id);
      const { newPassword } = req.body;
      
      if (!newPassword) {
        res.status(400).json({ success: false, error: '缺少新密码' });
        return;
      }

      await this.userModel.updatePassword(userId, newPassword);
      res.json({ success: true, message: '密码重置成功' });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  /**
   * 删除用户
   */
  public deleteUser = async (req: Request, res: Response) => {
    try {
      const userId = parseInt(req.params.id);
      await this.userModel.delete(userId);
      res.json({ success: true, message: 'User deleted successfully' });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };
}
