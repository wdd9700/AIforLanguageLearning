/**
 * @fileoverview 上下文管理器 (Context Manager)
 * @description
 * 负责管理 LLM 对话的上下文信息，包括会话历史、元数据和任务状态。
 * 上下文数据存储在本地文件系统中，并缓存在内存中以提高访问速度。
 * 
 * 主要功能：
 * 1. 上下文获取 (Get): 优先从内存获取，若不存在则尝试从磁盘加载，最后新建。
 * 2. 上下文持久化 (Save): 将内存中的上下文状态同步写入磁盘 JSON 文件。
 * 3. 上下文重置 (Reset): 归档当前会话文件，并开启一个新的空白会话。
 * 4. 历史记录管理 (History): 追加用户和 AI 的对话消息。
 * 5. 审计日志 (Audit): 记录关键操作日志到独立的审计文件中。
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import fs from 'fs/promises';
import path from 'path';
import { createLogger } from '../utils/logger';

const logger = createLogger('ContextManager');

/**
 * 会话上下文接口
 * 定义了存储在 JSON 文件中的数据结构
 */
export interface SessionContext {
  sessionId: string;
  userId: string;
  startTime: number;
  lastActive: number;
  task: string;
  model: string;
  history: Array<{ role: string; content: string; timestamp: number }>;
  metadata: Record<string, any>;
}

export class ContextManager {
  private sessionsDir: string;
  private auditDir: string;
  private activeSessions: Map<string, SessionContext> = new Map();

  constructor() {
    this.sessionsDir = path.join(__dirname, '../../data/sessions');
    this.auditDir = path.join(__dirname, '../../data/audit');
    // Ensure directories exist (async in constructor is tricky, usually done in init)
    // For now assuming directories are created by setup scripts or lazily
  }

  /**
   * 获取或创建会话上下文
   * 
   * 尝试获取指定会话 ID 的上下文数据。
   * 查找顺序：内存缓存 -> 磁盘文件 -> 创建新实例。
   * 
   * @param sessionId 会话唯一标识符
   * @param userId 用户 ID
   * @returns Promise<SessionContext> 会话上下文对象
   */
  public async getContext(sessionId: string, userId: string): Promise<SessionContext> {
    // 1. Check memory
    if (this.activeSessions.has(sessionId)) {
      return this.activeSessions.get(sessionId)!;
    }

    // 2. Check disk
    const filePath = this.getSessionPath(sessionId);
    try {
      const data = await fs.readFile(filePath, 'utf-8');
      const context = JSON.parse(data) as SessionContext;
      this.activeSessions.set(sessionId, context);
      return context;
    } catch (error) {
      // 3. Create new
      const newContext: SessionContext = {
        sessionId,
        userId,
        startTime: Date.now(),
        lastActive: Date.now(),
        task: 'default',
        model: 'default',
        history: [],
        metadata: {}
      };
      await this.saveContext(newContext);
      this.activeSessions.set(sessionId, newContext);
      return newContext;
    }
  }

  /**
   * 保存上下文到磁盘
   * 
   * 更新上下文的最后活跃时间，更新内存缓存，并将完整对象序列化写入磁盘文件。
   * 
   * @param context 需要保存的会话上下文对象
   */
  public async saveContext(context: SessionContext): Promise<void> {
    context.lastActive = Date.now();
    this.activeSessions.set(context.sessionId, context);
    
    const filePath = this.getSessionPath(context.sessionId);
    await fs.writeFile(filePath, JSON.stringify(context, null, 2));
  }

  /**
   * 重置上下文
   * 
   * 归档当前的会话文件（重命名添加时间戳），并创建一个新的空白会话上下文。
   * 用于开始新的对话场景或清除历史记忆。
   * 
   * @param sessionId 会话唯一标识符
   * @param userId 用户 ID
   * @returns Promise<SessionContext> 新创建的会话上下文
   */
  public async resetContext(sessionId: string, userId: string): Promise<SessionContext> {
    const filePath = this.getSessionPath(sessionId);
    
    try {
      // Archive existing
      await fs.access(filePath);
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const archivePath = path.join(this.sessionsDir, `${sessionId}_${timestamp}.json`);
      await fs.rename(filePath, archivePath);
      logger.info({ sessionId, archivePath }, 'Session context archived');
    } catch {
      // No existing file, ignore
    }

    this.activeSessions.delete(sessionId);
    return this.getContext(sessionId, userId);
  }

  /**
   * 添加消息到历史记录
   * 
   * 向指定会话的历史记录中追加一条新消息，并自动触发保存操作。
   * 
   * @param sessionId 会话唯一标识符
   * @param role 消息发送者角色 ('user' | 'assistant' | 'system')
   * @param content 消息内容
   */
  public async addMessage(sessionId: string, role: string, content: string): Promise<void> {
    const context = this.activeSessions.get(sessionId);
    if (context) {
      context.history.push({ role, content, timestamp: Date.now() });
      await this.saveContext(context);
    }
  }

  /**
   * 记录审计日志
   * 
   * 将关键操作记录到按日期分割的审计日志文件中。
   * 用于后续分析用户行为或排查问题。
   * 
   * @param sessionId 相关会话 ID
   * @param action 操作名称 (如 'start_analysis', 'query_vocab')
   * @param data 相关数据负载
   */
  public async logAudit(sessionId: string, action: string, data: any): Promise<void> {
    const date = new Date().toISOString().split('T')[0];
    const logFile = path.join(this.auditDir, `audit_${date}.log`);
    const entry = {
      timestamp: new Date().toISOString(),
      sessionId,
      action,
      data
    };
    await fs.appendFile(logFile, JSON.stringify(entry) + '\n');
  }

  private getSessionPath(sessionId: string): string {
    return path.join(this.sessionsDir, `${sessionId}.json`);
  }
}
