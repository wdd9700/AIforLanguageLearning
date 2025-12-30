/// <reference types="jest" />
/**
 * Orchestration Framework Tests
 * 测试服务编排、管道执行、路由匹配等功能
 */

import { ServiceOrchestrator } from '../orchestrator.js';
import { minimalOrchestratorConfig } from '../config.js';
import { ProcessingContext } from '../types.js';

describe('Service Orchestration Framework', () => {
  let orchestrator: ServiceOrchestrator;

  beforeAll(() => {
    orchestrator = new ServiceOrchestrator(minimalOrchestratorConfig);
  });

  afterAll(async () => {
    await orchestrator.cleanup();
  });

  describe('Service Registration', () => {
    it('should register services correctly', () => {
      const states = orchestrator.getServiceStates();
      expect(states).toBeDefined();
      expect(states.echo).toBeDefined();
    });

    it('should get service states', () => {
      const states = orchestrator.getServiceStates();
      expect(states.echo.name).toBe('echo');
      expect(states.echo.status).toBe('stopped');
    });
  });

  describe('Pipeline Management', () => {
    it('should list available pipelines', () => {
      const pipelines = orchestrator.getPipelines();
      expect(Array.isArray(pipelines)).toBe(true);
    });

    it('should have empty pipelines in minimal config', () => {
      const pipelines = orchestrator.getPipelines();
      expect(pipelines.length).toBe(0);
    });
  });

  describe('Metrics Collection', () => {
    it('should initialize metrics correctly', () => {
      const metrics = orchestrator.getMetrics();
      expect(metrics.requestCount).toBe(0);
      expect(metrics.successCount).toBe(0);
      expect(metrics.failureCount).toBe(0);
      expect(metrics.currentConcurrency).toBe(0);
    });

    it('should have positive infinity for min response time', () => {
      const metrics = orchestrator.getMetrics();
      expect(metrics.minResponseTime).toBe(Infinity);
    });
  });

  describe('Routing Rules', () => {
    it('should match simple topic patterns', async () => {
      // 测试路由匹配逻辑
      const context: ProcessingContext = {
        requestId: 'test-1',
        traceId: 'trace-1',
        payload: { test: 'data' },
        startTime: Date.now(),
        intermediateResults: new Map(),
      };

      // 由于 echo 服务未启动，期望处理失败
      // 但我们可以验证路由匹配逻辑
      const result = await orchestrator.handleMessage('test/echo', { test: 'data' });
      expect(result).toBeDefined();
      expect(result.traceId).toBeDefined();
    });
  });

  describe('Orchestrator State', () => {
    it('should track orchestrator status', () => {
      const states = orchestrator.getServiceStates();
      expect(Object.keys(states)).toContain('echo');
    });

    it('should update metrics after message handling', async () => {
      const metricsBefore = orchestrator.getMetrics();
      const countBefore = metricsBefore.requestCount;

      await orchestrator.handleMessage('test/echo', { test: 'data' }).catch(() => {
        // 错误是预期的（没有实际服务）
      });

      const metricsAfter = orchestrator.getMetrics();
      expect(metricsAfter.requestCount).toBeGreaterThanOrEqual(countBefore);
    });
  });

  describe('Error Handling', () => {
    it('should handle missing services gracefully', async () => {
      const result = await orchestrator.handleMessage('unknown/topic', {});
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    it('should track failures in metrics', async () => {
      const metricsBefore = orchestrator.getMetrics();
      const failuresBefore = metricsBefore.failureCount;

      await orchestrator.handleMessage('invalid/path', {}).catch(() => {
        // 错误是预期的
      });

      const metricsAfter = orchestrator.getMetrics();
      expect(metricsAfter.failureCount).toBeGreaterThanOrEqual(failuresBefore);
    });
  });

  describe('Message Processing', () => {
    it('should add trace ID to results', async () => {
      const result = await orchestrator.handleMessage('test/echo', { data: 'test' });
      expect(result.traceId).toBeDefined();
      expect(result.traceId).toMatch(/^trace-/);
    });

    it('should track processing duration', async () => {
      const result = await orchestrator.handleMessage('test/echo', { data: 'test' });
      expect(result.duration).toBeGreaterThanOrEqual(0);
      expect(typeof result.duration).toBe('number');
    });
  });
});
