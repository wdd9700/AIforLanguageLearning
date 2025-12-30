/**
 * @fileoverview 服务编排模块入口 (Service Orchestration Entry)
 * @description
 * 该模块统一导出了服务编排系统的所有核心组件和接口。
 * 
 * 包含组件：
 * - 类型定义 (types.ts)
 * - 服务抽象 (service.ts)
 * - 流水线管理 (pipeline.ts)
 * - 编排器核心 (orchestrator.ts)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

export * from './types.js';
export * from './service.js';
export * from './pipeline.js';
export * from './orchestrator.js';
export { ServiceOrchestrator as Orchestrator } from './orchestrator.js';
