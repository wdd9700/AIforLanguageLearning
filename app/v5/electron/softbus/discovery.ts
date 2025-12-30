/**
 * @fileoverview 服务发现模块 (Service Discovery Module)
 * @description
 * 该模块负责基于 mDNS 的服务发现与注册。
 * 
 * 主要功能包括：
 * 1. 服务注册与注销 (registerService, unregisterService)
 * 2. 服务查询 (lookupService)
 * 3. 发现事件监听 (on)
 * 4. 心跳维护 (startDiscovery, stopDiscovery)
 * 
 * 注意：当前实现为内存中的模拟实现，实际生产环境需集成 bonjour 或类似 mDNS 库。
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import { ServiceInfo, DiscoveryEvent } from './types.js';

/**
 * 服务发现管理器
 * 注：需引入 bonjour/mdns 库做实际 mDNS 广播
 * 这里提供接口定义，实现部分待补充
 */
export class DiscoveryManager {
  private services: Map<string, ServiceInfo> = new Map();
  private eventHandlers: ((event: DiscoveryEvent) => void)[] = [];
  private presenceInterval?: NodeJS.Timeout;

  /**
   * 注册服务
   */
  registerService(service: ServiceInfo): void {
    const key = `${service.peerId}:${service.name}`;
    this.services.set(key, service);

    this.emit({
      type: 'service-found',
      service,
      timestamp: Date.now(),
    });
  }

  /**
   * 注销服务
   */
  unregisterService(peerId: string, serviceName: string): void {
    const key = `${peerId}:${serviceName}`;
    const service = this.services.get(key);

    if (service) {
      this.services.delete(key);
      this.emit({
        type: 'service-lost',
        service,
        timestamp: Date.now(),
      });
    }
  }

  /**
   * 查询服务
   */
  lookupService(serviceName: string): ServiceInfo[] {
    return Array.from(this.services.values()).filter((svc) => svc.name === serviceName);
  }

  /**
   * 启动 mDNS 发现（心跳）
   * 实际应用中需要集成 bonjour 或类似库
   */
  startDiscovery(heartbeatIntervalMs: number = 5000): void {
    this.presenceInterval = setInterval(() => {
      const now = Date.now();
      for (const service of this.services.values()) {
        // 更新心跳时间戳
        if (now - service.heartbeatAt > heartbeatIntervalMs) {
          service.heartbeatAt = now;
        }
      }
    }, heartbeatIntervalMs);
  }

  /**
   * 停止发现
   */
  stopDiscovery(): void {
    if (this.presenceInterval) {
      clearInterval(this.presenceInterval);
      this.presenceInterval = undefined;
    }
  }

  /**
   * 监听发现事件
   */
  on(handler: (event: DiscoveryEvent) => void): void {
    this.eventHandlers.push(handler);
  }

  /**
   * 发出事件
   */
  private emit(event: DiscoveryEvent): void {
    for (const handler of this.eventHandlers) {
      try {
        handler(event);
      } catch (err) {
        console.error('[softbus-discovery] event handler error:', err);
      }
    }
  }

  /**
   * 列出所有服务
   */
  listServices(): ServiceInfo[] {
    return Array.from(this.services.values());
  }

  /**
   * 清空所有服务
   */
  clear(): void {
    this.services.clear();
  }
}
