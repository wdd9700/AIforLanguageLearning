/**
 * @fileoverview mDNS 广播与发现模块 (mDNS Service Discovery)
 * @description
 * 该文件封装了基于 Bonjour (Multicast DNS) 的服务发现机制，用于 Softbus 节点的自动组网。
 * 
 * 主要功能：
 * 1. 服务发布 (Advertising)：将当前后端实例的 Softbus 服务端口广播到局域网，使其可被前端或其他节点发现
 * 2. 服务发现 (Discovery)：扫描局域网内的其他 Softbus 节点，获取其连接端点 (Endpoint)
 * 
 * 技术实现：
 * - 使用 `bonjour-service` 库实现 mDNS 协议
 * - 默认服务类型为 `softbus`
 * - 支持携带 TXT 记录（如协议版本、节点 ID）
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

// bonjour-service 使用 CommonJS default export
import BonjourService from 'bonjour-service';

/**
 * mDNS 广播配置选项
 */
export interface MdnsAdvertiserOptions {
  port: number;
  name?: string;
  type?: string; // 默认 softbus
  txt?: Record<string, string>;
}

/**
 * mDNS 广播控制器接口
 */
export interface MdnsAdvertiser {
  stop: () => void;
}

/**
 * 启动 mDNS 广播
 * 发布当前服务，使其可被发现
 * 
 * @param options 广播配置选项
 * @returns 包含停止方法的控制器对象
 */
export function startMdnsAdvertiser(options: MdnsAdvertiserOptions): MdnsAdvertiser {
  const bonjour = new BonjourService();
  const service = bonjour.publish({
    name: options.name || 'language-softbus',
    type: options.type || 'softbus',
    port: options.port,
    txt: options.txt || { proto: 'zeromq' },
  });

  service.on('up', () => {
    // Service published
  });

  service.on('error', (err: any) => {
    console.warn('mDNS Service Error (non-fatal):', err.message);
  });

  const stop = () => {
    try {
      if (service && typeof service.stop === 'function') {
        service.stop(() => {
          bonjour.destroy();
        });
      } else {
        bonjour.destroy();
      }
    } catch (e) {
      bonjour.destroy();
    }
  };

  return { stop };
}

/**
 * 发现 Softbus 服务
 * 扫描局域网内的 Softbus 节点（可用于后端内部动态扩展）
 * 注：前端在 Electron 渲染进程亦可使用同样逻辑。
 * 
 * @param timeoutMs 扫描超时时间（毫秒），默认 2000ms
 * @returns 发现的服务端点列表 (tcp://host:port)
 */
export async function discoverSoftbus(timeoutMs: number = 2000): Promise<string[]> {
  const bonjour = new BonjourService();
  const endpoints: string[] = [];

  return new Promise((resolve) => {
    const browser = bonjour.find({ type: 'softbus' }, (service: any) => {
      const host = service.host || 'localhost';
      const port = service.port;
      endpoints.push(`tcp://${host}:${port}`);
    });

    setTimeout(() => {
      browser.stop();
      bonjour.destroy();
      resolve(endpoints);
    }, timeoutMs);
  });
}
