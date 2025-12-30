/**
 * @fileoverview Electron 预加载脚本 (Preload Script)
 * @description
 * 该脚本在渲染进程加载之前运行，用于安全地将主进程的功能暴露给渲染进程。
 * 通过 `contextBridge` 暴露 `window.api` 对象，实现隔离环境下的 IPC 通信。
 * 
 * 主要暴露的 API 包括：
 * 1. 事件订阅 (Event Subscriptions)：
 *    - 服务状态更新 (onServiceUpdate)
 *    - 快捷键触发 (onVocabularyHotkey, onTriggerLookup)
 *    - 软总线事件 (onSoftbusConnected, onSoftbusMessage, etc.)
 * 
 * 2. 配置管理 (Configuration Management)：
 *    - 获取/设置配置 (getConfig, setConfig)
 *    - 打开配置文件路径 (openConfigPath)
 * 
 * 3. 服务控制 (Service Control)：
 *    - 启动/停止服务 (startService, stopService)
 *    - 探测服务状态 (probeServices, getServiceState)
 * 
 * 4. 软总线接口 (Softbus API)：
 *    - 发布/订阅 (publish, subscribe)
 *    - RPC 调用 (rpc)
 *    - 流式传输 (streamOpen, streamSend)
 * 
 * 5. 编排器接口 (Orchestrator API)：
 *    - 执行流水线 (executePipeline)
 *    - 获取服务和指标 (getServices, getMetrics)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */
import { contextBridge, ipcRenderer } from 'electron';

// 预加载脚本：用 contextBridge 安全地把主进程能力暴露给渲染器
// 暴露的 API 需谨慎设计，只暴露必要的异步方法与事件订阅
contextBridge.exposeInMainWorld('api', {
 // 事件订阅
 onServiceUpdate: (cb: (evt: any) => void) => {
  const listener = (_e: any, payload: any) => cb(payload);
  ipcRenderer.on('service:update', listener);
  return () => ipcRenderer.removeListener('service:update', listener);
 },
 onVocabularyHotkey: (cb: () => void) => {
  const listener = () => cb();
  ipcRenderer.on('hotkey:vocabulary', listener);
  return () => ipcRenderer.removeListener('hotkey:vocabulary', listener);
 },
 onTriggerLookup: (cb: (data: { type: 'text' | 'image', content: string }) => void) => {
  const listener = (_e: any, data: any) => cb(data);
  ipcRenderer.on('trigger-lookup', listener);
  return () => ipcRenderer.removeListener('trigger-lookup', listener);
 },
 // Softbus 事件
 onSoftbusConnected: (cb: () => void) => {
  const listener = () => cb();
  ipcRenderer.on('softbus:connected', listener);
  return () => ipcRenderer.removeListener('softbus:connected', listener);
 },
 onSoftbusDisconnected: (cb: () => void) => {
  const listener = () => cb();
  ipcRenderer.on('softbus:disconnected', listener);
  return () => ipcRenderer.removeListener('softbus:disconnected', listener);
 },
 onSoftbusError: (cb: (err: any) => void) => {
  const listener = (_e: any, err: any) => cb(err);
  ipcRenderer.on('softbus:error', listener);
  return () => ipcRenderer.removeListener('softbus:error', listener);
 },
 onSoftbusMessage: (cb: (msg: any) => void) => {
  const listener = (_e: any, msg: any) => cb(msg);
  ipcRenderer.on('softbus:message', listener);
  return () => ipcRenderer.removeListener('softbus:message', listener);
 },
 onSoftbusStreamData: (cb: (data: any) => void) => {
  const listener = (_e: any, data: any) => cb(data);
  ipcRenderer.on('softbus:stream-data', listener);
  return () => ipcRenderer.removeListener('softbus:stream-data', listener);
 },
 onSoftbusStreamEnd: (cb: (info: any) => void) => {
  const listener = (_e: any, info: any) => cb(info);
  ipcRenderer.on('softbus:stream-end', listener);
  return () => ipcRenderer.removeListener('softbus:stream-end', listener);
 },
 
 // 配置管理
 getConfig: () => ipcRenderer.invoke('config:get'),
 setConfig: (patch: any) => ipcRenderer.invoke('config:set', patch),
 openConfigPath: () => ipcRenderer.invoke('config:open-path'),
 
 // 服务控制与状态查询
 startService: (key: string) => ipcRenderer.invoke('service:start', key),
 stopService: (key: string) => ipcRenderer.invoke('service:stop', key),
 probeServices: () => ipcRenderer.invoke('service:probe'),
 getServiceState: () => ipcRenderer.invoke('service:state'),
 
 // 悬浮层控制（无需 HTTP）
 overlayShow: (title: string, text: string) => ipcRenderer.invoke('overlay:show', { title, text }),
 
 // Softbus API (软总线接口)
 softbus: {
  status: () => ipcRenderer.invoke('softbus:status'),
  publish: (topic: string, data: any, contentType?: string) => 
    ipcRenderer.invoke('softbus:publish', { topic, data, contentType }),
  subscribe: (topic: string) => ipcRenderer.invoke('softbus:subscribe', { topic }),
  unsubscribe: (topic: string) => ipcRenderer.invoke('softbus:unsubscribe', { topic }),
  rpc: (method: string, params?: any, timeout?: number) => 
    ipcRenderer.invoke('softbus:rpc', { method, params, timeout }),
  streamOpen: (streamId: string, topic: string) => 
    ipcRenderer.invoke('softbus:stream-open', { streamId, topic }),
  streamSend: (streamId: string, data: any) => 
    ipcRenderer.invoke('softbus:stream-send', { streamId, data }),
  streamEnd: (streamId: string) => 
    ipcRenderer.invoke('softbus:stream-end', { streamId }),
  disconnect: () => ipcRenderer.invoke('softbus:disconnect'),
 },

 // Orchestrator API (服务编排接口)
 orchestrator: {
  status: () => ipcRenderer.invoke('orchestrator:status'),
  getServices: () => ipcRenderer.invoke('orchestrator:services'),
  getMetrics: () => ipcRenderer.invoke('orchestrator:metrics'),
  executePipeline: (name: string, data: any) => 
    ipcRenderer.invoke('orchestrator:execute-pipeline', { name, data }),
  send: (topic: string, data: any, contentType?: string) => 
    ipcRenderer.invoke('orchestrator:send', { topic, data, contentType }),
 }
});

declare global { interface Window { api: any } }
