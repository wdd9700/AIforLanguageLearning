/**
 * @fileoverview 软总线集成测试模块 (Softbus Integration Test)
 * @description
 * 该模块用于测试 Electron 主进程与软总线的集成功能。
 * 
 * 主要测试场景包括：
 * 1. 发布/订阅 (Pub/Sub)：测试消息发布和接收
 * 2. RPC 调用 (RPC)：测试远程过程调用和响应
 * 3. 双向流 (Bidirectional Streaming)：测试流的打开、发送数据和关闭
 * 
 * 此外，还提供了监控功能 (setupSoftbusMonitoring)，用于实时记录连接状态和消息流。
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import log from 'electron-log';

/**
 * Echo test: Send message to server and receive response
 * This tests basic pub/sub and RPC functionality
 */
export async function runSoftbusEchoTest(): Promise<void> {
  try {
    log.info('Softbus: Starting echo test...');
    
    // Test 1: Pub/Sub
    log.info('Test 1: Publishing test message');
    const pubResult = await (window as any).api.softbus.publish(
      'test/echo',
      JSON.stringify({ msg: 'Hello from Electron' }),
      'application/json'
    );
    
    if (!pubResult.ok) {
      log.warn('Publish failed:', pubResult.error);
    } else {
      log.info('Publish OK');
    }
    
    // Test 2: RPC
    log.info('Test 2: Sending RPC request');
    const rpcResult = await (window as any).api.softbus.rpc(
      'echo',
      { message: 'Hello from RPC' },
      5000
    );
    
    if (!rpcResult.ok) {
      log.warn('RPC failed:', rpcResult.error);
    } else {
      log.info('RPC response:', rpcResult.data);
    }
    
    // Test 3: Stream
    log.info('Test 3: Opening stream');
    const streamOpenResult = await (window as any).api.softbus.streamOpen(
      'test-stream-1',
      'test/stream'
    );
    
    if (!streamOpenResult.ok) {
      log.warn('Stream open failed:', streamOpenResult.error);
    } else {
      log.info('Stream opened');
      
      // Send data on stream
      await (window as any).api.softbus.streamSend(
        'test-stream-1',
        'Hello from stream'
      );
      
      // Close stream
      await (window as any).api.softbus.streamEnd('test-stream-1');
      log.info('Stream closed');
    }
    
    log.info('Softbus: Echo test completed');
  } catch (error) {
    log.error('Softbus echo test error:', error);
  }
}

/**
 * Monitor Softbus connection and messages
 */
export function setupSoftbusMonitoring(): void {
  // Monitor connection status
  (window as any).api.onSoftbusConnected?.(() => {
    log.info('Softbus: Connected');
  });
  
  (window as any).api.onSoftbusDisconnected?.(() => {
    log.warn('Softbus: Disconnected');
  });
  
  (window as any).api.onSoftbusError?.((err: any) => {
    log.error('Softbus: Error', err);
  });
  
  // Monitor incoming messages
  (window as any).api.onSoftbusMessage?.((msg: any) => {
    log.info('Softbus message received:', {
      topic: msg.topic,
      msgId: msg.msgId,
      contentType: msg.contentType,
      payloadLength: msg.payload.length,
    });
  });
  
  // Monitor stream data
  (window as any).api.onSoftbusStreamData?.((data: any) => {
    log.info('Softbus stream data:', {
      streamId: data.streamId,
      dataLength: data.data.length,
    });
  });
  
  (window as any).api.onSoftbusStreamEnd?.((info: any) => {
    log.info('Softbus stream ended:', info.streamId);
  });
}
