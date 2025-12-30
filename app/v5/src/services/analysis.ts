/**
 * @fileoverview 学习分析服务模块 (Analysis Service)
 * @description 提供学习数据统计和智能分析功能。
 *              负责获取用户的学习进度概览，以及针对特定维度（如词汇、语法）的深度分析报告。
 */

import api from './api';

/** 学习统计数据接口 */
export interface LearningStats {
  /** 已掌握/查询的词汇数量 */
  vocabulary: number;
  /** 已批改的作文篇数 */
  essay: number;
  /** 完成的语音对话次数 */
  dialogue: number;
  /** 生成的分析报告数量 */
  analysis: number;
}

/** 深度分析结果接口 */
export interface AnalysisResult {
  /** 分析维度 (如 'vocabulary', 'grammar', 'fluency') */
  dimension: string;
  /** 综合评分 (0-100) */
  score: number;
  /** 趋势变化 (如 +5, -2) */
  trend: number;
  /** 关键洞察/评价列表 */
  insights: string[];
  /** 改进建议列表 */
  recommendations: string[];
  /** 可视化图表数据 */
  visualization: {
    /** 图表类型 */
    type: 'radar' | 'line' | 'bar';
    /** 图表标题 */
    title: string;
    /** X轴或雷达图维度的标签 */
    labels: string[];
    /** 数据集 */
    datasets: Array<{
      label: string;
      data: number[];
    }>;
  };
}

export const AnalysisService = {
  /**
   * 获取学习统计概览
   * 
   * 获取用户在各个模块（词汇、作文、对话）的累计学习数据。
   * 
   * @returns {Promise<LearningStats>} 统计数据对象
   * @throws {Error} 如果获取失败
   */
  async getStats(): Promise<LearningStats> {
    const response = await api.get<{ success: boolean; data: LearningStats }>('/api/learning/stats');
    const result = response as unknown as { success: boolean; data: LearningStats; error?: string };
    if (result.success) {
      return result.data;
    }
    throw new Error(result.error || '获取统计数据失败');
  },

  /**
   * 执行深度学习分析
   * 
   * 请求后端对指定维度进行智能分析，生成包含评分、建议和图表数据的报告。
   * 
   * @param {string} dimension - 分析维度 (如 'vocabulary')
   * @returns {Promise<AnalysisResult>} 分析报告结果
   * @throws {Error} 如果分析失败
   */
  async analyze(dimension: string): Promise<AnalysisResult> {
    const response = await api.post<{ success: boolean; data: AnalysisResult }>('/api/learning/analyze', { dimension });
    const result = response as unknown as { success: boolean; data: AnalysisResult; error?: string };
    if (result.success) {
      return result.data;
    }
    throw new Error(result.error || '分析失败');
  }
};
