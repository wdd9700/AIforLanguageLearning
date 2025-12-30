<script setup lang="ts">
/**
 * @fileoverview 学习分析视图组件 (AnalysisView)
 * @description 展示用户的学习进度和能力分析图表。
 *              包含概览统计卡片和基于 ECharts 的可视化图表（雷达图、折线图）。
 */

import { ref, onMounted } from 'vue';
import { AnalysisService, type LearningStats, type AnalysisResult } from '../services/analysis';
import BaseChart from '../components/BaseChart.vue';

// --- 状态管理 ---

/** 当前激活的标签页 (默认为 'overview') */
const activeTab = ref('overview');

/** 学习统计数据 (顶部卡片) */
const stats = ref<LearningStats>({ vocabulary: 0, essay: 0, dialogue: 0, analysis: 0 });

/** 加载状态 */
const isLoading = ref(false);

/** 词汇量趋势图表配置 (折线图) */
const vocabChartOption = ref<any>(null);

/** 综合能力图表配置 (雷达图) */
const skillsChartOption = ref<any>(null);

// --- 图表配置生成 ---

/**
 * 根据后端返回的可视化数据生成 ECharts 配置对象
 * 
 * @param {AnalysisResult['visualization']} viz - 后端返回的可视化数据结构
 * @returns {Object} ECharts 配置对象
 */
const createChartOption = (viz: AnalysisResult['visualization']) => {
  const commonOptions = {
    backgroundColor: 'transparent',
    title: { text: viz.title, textStyle: { color: '#fff' } },
    tooltip: { trigger: 'axis' },
  };

  if (viz.type === 'radar') {
    // 雷达图配置 (用于综合能力展示)
    return {
      ...commonOptions,
      radar: {
        indicator: viz.labels.map(label => ({ name: label, max: 100 })),
        axisName: { color: '#ccc' }
      },
      series: [{
        type: 'radar',
        data: viz.datasets.map(ds => ({
          value: ds.data,
          name: ds.label
        })),
        areaStyle: { color: 'rgba(99, 102, 241, 0.5)' },
        lineStyle: { color: '#6366f1' }
      }]
    };
  } else if (viz.type === 'line') {
    // 折线图配置 (用于趋势展示)
    return {
      ...commonOptions,
      xAxis: { 
        type: 'category', 
        data: viz.labels, 
        axisLabel: { color: '#ccc' } 
      },
      yAxis: { 
        type: 'value', 
        axisLabel: { color: '#ccc' }, 
        splitLine: { lineStyle: { color: '#333' } } 
      },
      series: viz.datasets.map(ds => ({
        name: ds.label,
        type: 'line',
        data: ds.data,
        smooth: true,
        itemStyle: { color: '#6366f1' }
      }))
    };
  }
  return {};
};

/**
 * 加载分析图表数据
 * 
 * 分别请求 'Overall' (综合) 和 'Vocabulary' (词汇) 的分析数据，
 * 并生成对应的图表配置。
 */
const loadAnalysis = async () => {
  try {
    // 加载综合能力分析 (雷达图)
    const overallResult = await AnalysisService.analyze('Overall');
    if (overallResult.visualization) {
      skillsChartOption.value = createChartOption(overallResult.visualization);
    }

    // 加载词汇量趋势分析 (折线图)
    const vocabResult = await AnalysisService.analyze('Vocabulary');
    if (vocabResult.visualization) {
      vocabChartOption.value = createChartOption(vocabResult.visualization);
    }
  } catch (e) {
    console.error('Failed to load analysis charts', e);
  }
};

// --- 生命周期 ---

onMounted(async () => {
  try {
    isLoading.value = true;
    // 并行加载统计数据和图表数据
    const [statsData] = await Promise.all([
      AnalysisService.getStats(),
      loadAnalysis()
    ]);
    stats.value = statsData;
  } catch (e) {
    console.error('Failed to load stats', e);
  } finally {
    isLoading.value = false;
  }
});
</script>

<template>
  <div class="p-8 h-full overflow-y-auto">
    <div class="flex justify-between items-center mb-8">
      <h2 class="text-2xl font-bold text-white">学习分析</h2>
      <div class="flex space-x-2 bg-gray-800 p-1 rounded-lg">
        <button 
          v-for="tab in ['overview', 'vocabulary', 'progress']" 
          :key="tab"
          @click="activeTab = tab"
          class="px-4 py-2 rounded-md text-sm transition-colors capitalize"
          :class="activeTab === tab ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'"
        >
          {{ tab }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div class="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <div class="text-gray-400 text-sm mb-2">词汇记录</div>
        <div class="text-3xl font-bold text-white">{{ stats.vocabulary }} <span class="text-sm text-gray-500 font-normal">个</span></div>
      </div>
      <div class="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <div class="text-gray-400 text-sm mb-2">作文批改</div>
        <div class="text-3xl font-bold text-white">{{ stats.essay }} <span class="text-sm text-gray-500 font-normal">篇</span></div>
      </div>
      <div class="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <div class="text-gray-400 text-sm mb-2">语音对话</div>
        <div class="text-3xl font-bold text-white">{{ stats.dialogue }} <span class="text-sm text-gray-500 font-normal">次</span></div>
      </div>
      <div class="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <div class="text-gray-400 text-sm mb-2">智能分析</div>
        <div class="text-3xl font-bold text-white">{{ stats.analysis }} <span class="text-sm text-gray-500 font-normal">次</span></div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-gray-800 rounded-xl p-6 border border-gray-700 h-80 flex items-center justify-center">
        <BaseChart v-if="vocabChartOption" :options="vocabChartOption" class="w-full h-full" />
        <div v-else class="text-gray-500">加载中...</div>
      </div>
      <div class="bg-gray-800 rounded-xl p-6 border border-gray-700 h-80 flex items-center justify-center">
        <BaseChart v-if="skillsChartOption" :options="skillsChartOption" class="w-full h-full" />
        <div v-else class="text-gray-500">加载中...</div>
      </div>
    </div>
  </div>
</template>
