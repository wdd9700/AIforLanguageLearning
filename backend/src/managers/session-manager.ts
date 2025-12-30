/**
 * @fileoverview 会话管理器 (Session Manager)
 * @description
 * 该文件负责管理客户端会话的完整生命周期，支持多设备登录和状态持久化。
 * 
 * 主要功能：
 * 1. 会话创建：生成唯一的 Session ID，记录客户端设备信息 (Peer ID) 和能力 (Capabilities)
 * 2. 身份绑定：将匿名会话与用户 ID 关联，实现登录状态管理
 * 3. 心跳保活：处理客户端心跳，更新最后活跃时间
 * 4. 过期清理：定期扫描并移除超时未活跃的会话
 * 5. 持久化：将会话状态同步到 SQLite 数据库，确保服务重启后会话不丢失
 * 6. 多端管理：支持查询特定用户的所有活跃会话
 * 
 * 待改进项：
 * - [ ] 引入 Redis 替代内存 Map 以支持分布式部署
 * - [ ] 增加会话互踢机制 (单点登录策略)
 * - [ ] 记录更详细的客户端指纹信息
 * - [ ] 统一 Orchestrator 和 Managers 中的 SessionManager 实现
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { v4 as uuidv4 } from 'uuid';
import { Session } from '../shared/types';
import { createLogger } from '../utils/logger';
import { config } from '../config/env';
import { Database } from '../database/db';

const logger = createLogger('SessionManager');

export class SessionManager {
  private sessions: Map<string, Session> = new Map();
  private cleanupInterval: NodeJS.Timeout | null = null;
  private db: Database | null = null;

  constructor(db?: Database) {
    if (db) {
        this.db = db;
        this.loadSessionsFromDb();
    }
    this.startCleanupTask();
  }

  /**
   * 从数据库加载活跃会话
   * 在服务启动时恢复之前的会话状态
   */
  private async loadSessionsFromDb() {
    if (!this.db) return;
    try {
        const rows = await this.db.all<any>('SELECT * FROM sessions');
        for (const row of rows) {
            const session: Session = {
                id: row.session_id,
                peerId: row.peer_id,
                userId: row.user_id ? row.user_id.toString() : undefined,
                capabilities: JSON.parse(row.capabilities),
                createdAt: row.created_at,
                lastHeartbeat: row.last_heartbeat,
                isAuthenticated: !!row.user_id
            };
            this.sessions.set(session.id, session);
        }
        logger.info({ count: this.sessions.size }, 'Sessions loaded from DB');
    } catch (error) {
        logger.error({ error }, 'Failed to load sessions from DB');
    }
  }

  /**
   * 持久化会话到数据库
   * 插入或更新会话记录
   */
  private async persistSession(session: Session) {
    if (!this.db) return;
    try {
        await this.db.run(`
            INSERT OR REPLACE INTO sessions (session_id, user_id, peer_id, capabilities, created_at, last_heartbeat)
            VALUES (?, ?, ?, ?, ?, ?)
        `, [
            session.id,
            session.userId ? parseInt(session.userId) : null,
            session.peerId,
            JSON.stringify(session.capabilities),
            session.createdAt,
            session.lastHeartbeat
        ]);
    } catch (error) {
        logger.error({ sessionId: session.id, error }, 'Failed to persist session');
    }
  }

  /**
   * 从数据库移除会话
   */
  private async removeSessionFromDb(sessionId: string) {
    if (!this.db) return;
    try {
        await this.db.run('DELETE FROM sessions WHERE session_id = ?', [sessionId]);
    } catch (error) {
        logger.error({ sessionId, error }, 'Failed to remove session from DB');
    }
  }

  /**
   * 创建新会话
   * 生成唯一 Session ID，并初始化状态
   * @param peerId 客户端设备 ID
   * @param capabilities 客户端能力描述
   */
  createSession(peerId: string, capabilities: any): string {
    const sessionId = uuidv4();
    const now = Date.now();

    const session: Session = {
      id: sessionId,
      peerId,
      createdAt: now,
      lastHeartbeat: now,
      capabilities,
      isAuthenticated: false,
    };

    this.sessions.set(sessionId, session);
    this.persistSession(session); // 异步持久化
    logger.info({ sessionId, peerId }, 'Session created');

    return sessionId;
  }

  /**
   * 获取会话信息
   */
  getSession(sessionId: string): Session | undefined {
    return this.sessions.get(sessionId);
  }

  /**
   * 绑定用户到会话
   * 将匿名会话转换为已认证会话
   */
  bindUser(sessionId: string, userId: string): void {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error('Session not found');
    }

    session.userId = userId;
    session.isAuthenticated = true;
    this.persistSession(session); // 更新数据库

    logger.info({ sessionId, userId }, 'User bound to session');
  }

  /**
   * 更新心跳时间
   * 保持会话活跃，防止被清理
   */
  updateHeartbeat(sessionId: string): void {
    const session = this.sessions.get(sessionId);
    if (!session) {
      return;
    }

    session.lastHeartbeat = Date.now();
    // 优化：不每次心跳都写数据库，避免 IO 压力
    // 仅在关键状态变更或定期批量更新时写入
  }

  /**
   * 删除会话
   * 从内存和数据库中移除
   */
  deleteSession(sessionId: string): void {
    const session = this.sessions.get(sessionId);
    if (session) {
      this.sessions.delete(sessionId);
      this.removeSessionFromDb(sessionId);
      logger.info({ sessionId }, 'Session deleted');
    }
  }

  /**
   * 获取指定用户的所有活跃会话
   * 用于多端登录管理
   */
  getUserSessions(userId: string): Session[] {
    const sessions: Session[] = [];
    for (const session of this.sessions.values()) {
      if (session.userId === userId) {
        sessions.push(session);
      }
    }
    return sessions;
  }

  /**
   * 启动定期清理任务
   */
  private startCleanupTask(): void {
    this.cleanupInterval = setInterval(() => {
      this.cleanupExpiredSessions();
    }, config.session.heartbeatInterval);
  }

  /**
   * 清理过期会话
   * 移除超过超时时间未发送心跳的会话
   */
  private cleanupExpiredSessions(): void {
    const now = Date.now();
    const timeout = config.session.timeout;

    for (const [sessionId, session] of this.sessions.entries()) {
      if (now - session.lastHeartbeat > timeout) {
        this.deleteSession(sessionId);
        logger.info({ sessionId }, 'Session expired and removed');
      }
    }
  }

  /**
   * 获取会话统计信息
   */
  getStats(): { total: number; authenticated: number; anonymous: number } {
    let authenticated = 0;
    let anonymous = 0;

    for (const session of this.sessions.values()) {
      if (session.isAuthenticated) {
        authenticated++;
      } else {
        anonymous++;
      }
    }

    return {
      total: this.sessions.size,
      authenticated,
      anonymous,
    };
  }

  /**
   * 清理所有资源
   * 停止定时任务并清空会话
   */
  async cleanup(): Promise<void> {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }

    this.sessions.clear();
    logger.info('Session manager cleaned up');
  }
}
