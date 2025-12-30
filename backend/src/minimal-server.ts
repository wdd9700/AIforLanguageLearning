/**
 * @fileoverview 最小化测试服务器 (Minimal Test Server)
 * 
 * 该文件提供了一个轻量级的服务器实现，用于快速验证网络连通性和环境配置。
 * 
 * 主要功能：
 * 1. 基础 HTTP 服务：提供健康检查接口 (/health)
 * 2. WebSocket 服务：提供简单的回显 (Echo) 功能，用于测试实时通信通道
 * 3. 错误诊断：捕获并打印启动错误
 * 
 * 适用场景：
 * - 初始环境搭建时的连通性测试
 * - 排查网络防火墙或端口占用问题
 * - 验证 WebSocket 客户端连接
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */
import express from 'express';
import http from 'http';
import { WebSocketServer } from 'ws';

const PORT = 3000;
const app = express();
const httpServer = http.createServer(app);
const wss = new WebSocketServer({ server: httpServer, path: '/stream' });

// 基础健康检查路由
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: Date.now() });
});

// 根路由
app.get('/', (req, res) => {
  res.send('<h1>Minimal Server Running</h1>');
});

// WebSocket 连接处理
wss.on('connection', (ws) => {
  console.log('✓ WebSocket 客户端已连接');
  
  ws.on('message', (data) => {
    console.log('收到消息:', data.toString().substring(0, 100));
    // 回显消息，用于测试双向通信
    ws.send(JSON.stringify({ type: 'echo', data: data.toString() }));
  });

  ws.on('close', () => {
    console.log('✗ WebSocket 客户端已断开');
  });
});

// 启动服务器
httpServer.listen(PORT, '0.0.0.0', () => {
  console.log('='.repeat(60));
  console.log('✓ 最小化服务器启动成功!');
  console.log(`✓ HTTP 服务:      http://localhost:${PORT}`);
  console.log(`✓ 健康检查:       http://localhost:${PORT}/health`);
  console.log(`✓ WebSocket 服务: ws://localhost:${PORT}/stream`);
  console.log('='.repeat(60));
});

// 错误处理
httpServer.on('error', (err: any) => {
  console.error('✗ 服务器错误:', err.message);
  console.error('  错误代码:', err.code);
  console.error('  端口:', PORT);
});

// 优雅关闭
process.on('SIGINT', () => {
  console.log('\n✓ 正在关闭服务器...');
  httpServer.close(() => {
    console.log('✓ 服务器已关闭');
    process.exit(0);
  });
});
