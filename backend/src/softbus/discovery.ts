/**
 * @fileoverview 软总线服务发现模块 (Softbus Discovery)
 * 
 * 负责基于 mDNS 的服务注册、发现和心跳维护。
 * 管理本地和远程服务的生命周期，提供服务查询和事件通知机制。
 * 
 * 主要功能：
 * 1. 服务注册 (Register)：将服务信息添加到本地注册表，并广播发现事件
 * 2. 服务注销 (Unregister)：移除服务并通知服务丢失
 * 3. 服务查询 (Lookup)：根据名称查找可用服务实例
 * 4. 心跳维护 (Heartbeat)：定期更新服务活跃状态
 * 5. 事件通知：支持监听 'service-found' 和 'service-lost' 事件
 * 
 * 待改进项：
 * 1. 集成真实的 mDNS 库 (如 bonjour 或 multicast-dns) 以实现跨设备发现
 * 2. 实现分布式服务注册表同步机制
 * 3. 增加服务元数据 (Metadata) 的动态更新支持
 * 4. 优化心跳机制，减少网络广播风暴
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import { ServiceInfo, DiscoveryEvent } from './types';

/**
 * 服务发现管理器
 * 管理本地和远程服务的生命周期，提供服务查询和事件通知
 * 注：实际的 mDNS 广播需集成 bonjour 或 multicast-dns 库
 */
export class DiscoveryManager {
  private services: Map<string, ServiceInfo> = new Map();
  private eventHandlers: ((event: DiscoveryEvent) => void)[] = [];
  private presenceInterval?: NodeJS.Timeout;

  /**
   * 注册服务
   * 将服务信息添加到本地注册表，并触发发现事件
   * @param service 服务信息对象
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
   * 从注册表中移除服务，并触发服务丢失事件
   * @param peerId 节点 ID
   * @param serviceName 服务名称
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
   * 根据服务名称查找所有可用的服务实例
   * @param serviceName 服务名称
   * @returns 服务信息列表
   */
  lookupService(serviceName: string): ServiceInfo[] {
    return Array.from(this.services.values()).filter((svc) => svc.name === serviceName);
  }

  /**
   * 启动服务发现 (心跳机制)
   * 定期更新服务的心跳时间戳，维持服务活跃状态
   * @param heartbeatIntervalMs 心跳间隔 (默认 5000ms)
   */
  startDiscovery(heartbeatIntervalMs: number = 5000): void {
    this.presenceInterval = setInterval(() => {
      const now = Date.now();
      for (const service of this.services.values()) {
        // 模拟心跳更新 (实际应由网络层触发)
        if (now - service.heartbeatAt > heartbeatIntervalMs) {
          service.heartbeatAt = now;
        }
      }
    }, heartbeatIntervalMs);
  }

  /**
   * 停止服务发现
   * 清除心跳定时器
   */
  stopDiscovery(): void {
    if (this.presenceInterval) {
      clearInterval(this.presenceInterval);
      this.presenceInterval = undefined;
    }
  }

  /**
   * 监听发现事件
   * @param handler 事件处理函数
   */
  on(handler: (event: DiscoveryEvent) => void): void {
    this.eventHandlers.push(handler);
  }

  /**
   * 触发事件
   * @param event 发现事件对象
   */
  private emit(event: DiscoveryEvent): void {
    for (const handler of this.eventHandlers) {
      try {
        handler(event);
      } catch (err) {
        console.error('[softbus-discovery] 事件处理错误:', err);
      }
    }
  }

  /**
   * 列出所有已发现的服务
   * @returns 服务信息列表
   */
  listServices(): ServiceInfo[] {
    return Array.from(this.services.values());
  }

  /**
   * 清空所有服务记录
   */
  clear(): void {
    this.services.clear();
  }
}
