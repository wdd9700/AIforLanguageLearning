<script setup lang="ts">
/**
 * @fileoverview 作文批改视图组件 (EssayView)
 * @description 提供作文输入和智能批改功能。
 *              支持文本输入和图片 OCR 识别。
 *              展示批改结果，包括多维度评分雷达图、详细评语和修改建议。
 */

import { ref, onMounted, onUnmounted, computed } from 'vue';
import { EssayService } from '../services/essay';
import type { EssayCorrectionResult } from '../types/essay';
import StarRating from '../components/StarRating.vue';
import BaseChart from '../components/BaseChart.vue';

// --- 状态管理 ---

/** 作文内容输入 */
const essayText = ref('');

/** 是否正在处理 (批改或 OCR) */
const isProcessing = ref(false);

/** 批改结果数据 */
const result = ref<EssayCorrectionResult | null>(null);

/** 错误提示信息 */
const errorMsg = ref('');

// --- 计算属性 ---

/**
 * 雷达图配置 (基于 ECharts)
 * 
 * 根据批改结果中的各项分数生成雷达图配置。
 * 维度包括：词汇、语法、逻辑、流畅度、内容、结构。
 */
const radarOption = computed(() => {
  if (!result.value) return null;
  const s = result.value.scores;
  return {
    backgroundColor: 'transparent',
    radar: {
      indicator: [
        { name: '词汇', max: 100 },
        { name: '语法', max: 100 },
        { name: '逻辑', max: 100 },
        { name: '流畅度', max: 100 },
        { name: '内容', max: 100 },
        { name: '结构', max: 100 }
      ],
      axisName: { color: '#9ca3af', fontSize: 12 },
      splitArea: { show: false },
      splitLine: { lineStyle: { color: '#374151' } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: [s.vocabulary, s.grammar, s.logic, s.fluency, s.content, s.structure],
        name: 'Essay Score'
      }],
      areaStyle: { color: 'rgba(99, 102, 241, 0.2)' },
      lineStyle: { color: '#6366f1', width: 2 },
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: { color: '#818cf8' }
    }]
  };
});

// --- 方法定义 ---

/**
 * 处理作文批改
 * 
 * 调用 EssayService.correct 提交文本进行批改。
 */
const handleCorrection = async () => {
  const text = essayText.value.trim();
  if (!text) return;
  
  isProcessing.value = true;
  errorMsg.value = '';
  result.value = null;

  try {
    const res = await EssayService.correct(text);
    result.value = res;
  } catch (err: any) {
    console.error(err);
    errorMsg.value = err.message || '批改失败，请稍后重试';
  } finally {
    isProcessing.value = false;
  }
};

/**
 * 处理粘贴事件 (支持图片 OCR)
 * 
 * 监听粘贴事件，如果包含图片，则调用 EssayService.correctOCR 进行识别和批改。
 * 
 * @param {ClipboardEvent} event - 剪贴板事件
 */
const handlePaste = async (event: ClipboardEvent) => {
  const items = event.clipboardData?.items;
  if (!items) return;

  for (const item of items) {
    if (item.type.indexOf('image') !== -1) {
      const blob = item.getAsFile();
      if (!blob) continue;

      isProcessing.value = true;
      errorMsg.value = '';
      result.value = null;
      essayText.value = '[正在识别图片...]';

      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64 = e.target?.result as string;
        try {
          // 调用 OCR 批改服务
          const res = await EssayService.correctOCR(base64);
          result.value = res;
          essayText.value = res.original || '[OCR 完成]'; 
        } catch (err: any) {
          console.error(err);
          errorMsg.value = err.message || 'OCR 识别失败';
          essayText.value = '';
        } finally {
          isProcessing.value = false;
        }
      };
      reader.readAsDataURL(blob);
      break; 
    }
  }
};

onMounted(() => {
  document.addEventListener('paste', handlePaste);
});

onUnmounted(() => {
  document.removeEventListener('paste', handlePaste);
});
</script>

<template>
  <div class="h-full flex flex-col p-8 max-w-6xl mx-auto">
    <!-- Input Area -->
    <div class="relative mb-6 flex-shrink-0">
      <textarea
        v-model="essayText"
        class="w-full h-32 px-6 py-4 bg-gray-800 border border-gray-700 rounded-xl text-white text-lg focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/50 outline-none transition-all shadow-lg resize-none custom-scrollbar"
        placeholder="输入作文内容或直接粘贴图片 (Ctrl+V)..."
      ></textarea>
      <div class="absolute right-3 bottom-3 flex items-center space-x-2">
        <span v-if="isProcessing" class="text-indigo-400 text-sm animate-pulse mr-2">AI 批改中...</span>
        <button
          @click="handleCorrection"
          class="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors font-medium"
          :disabled="isProcessing"
        >
          开始批改
        </button>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="errorMsg" class="bg-red-900/50 border border-red-700 text-red-200 px-6 py-4 rounded-xl mb-6 flex-shrink-0">
      {{ errorMsg }}
    </div>

    <!-- Result Area -->
    <div class="flex-1 bg-gray-900 rounded-xl border border-gray-700 shadow-inner overflow-hidden flex flex-col">
      <div class="flex-1 overflow-y-auto p-8 custom-scrollbar">
        <div v-if="result" class="text-gray-300 font-mono text-sm leading-relaxed whitespace-pre-wrap space-y-8">
          
          <!-- Header: Score & Radar -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-8 border-b border-gray-700 pb-8">
            <!-- Left: Total Score -->
            <div class="md:col-span-1 flex flex-col justify-center items-center bg-gray-800/30 rounded-xl p-6 border border-gray-700/50">
              <div class="text-gray-400 uppercase tracking-widest text-xs mb-2">Total Score</div>
              <StarRating :score="result.scores.total" class="mb-4" />
              
              <div class="w-full space-y-2 mt-4">
                <div class="flex justify-between text-xs">
                  <span class="text-gray-500">Vocabulary</span>
                  <span class="text-indigo-300">{{ result.scores.vocabulary }}</span>
                </div>
                <div class="flex justify-between text-xs">
                  <span class="text-gray-500">Grammar</span>
                  <span class="text-indigo-300">{{ result.scores.grammar }}</span>
                </div>
                <div class="flex justify-between text-xs">
                  <span class="text-gray-500">Logic</span>
                  <span class="text-indigo-300">{{ result.scores.logic }}</span>
                </div>
                <div class="flex justify-between text-xs">
                  <span class="text-gray-500">Fluency</span>
                  <span class="text-indigo-300">{{ result.scores.fluency }}</span>
                </div>
                <div class="flex justify-between text-xs">
                  <span class="text-gray-500">Content</span>
                  <span class="text-indigo-300">{{ result.scores.content }}</span>
                </div>
                <div class="flex justify-between text-xs">
                  <span class="text-gray-500">Structure</span>
                  <span class="text-indigo-300">{{ result.scores.structure }}</span>
                </div>
              </div>
            </div>

            <!-- Right: Radar Chart -->
            <div class="md:col-span-2 h-64">
              <BaseChart v-if="radarOption" :options="radarOption" />
            </div>
          </div>

          <!-- Evaluation -->
          <div v-if="result.evaluation">
            <h3 class="text-white font-bold mb-3 uppercase tracking-wider text-xs flex items-center">
              <span class="w-1 h-4 bg-indigo-500 mr-2 rounded-full"></span>
              综合评价
            </h3>
            <div class="pl-4 text-gray-300 leading-7">
              {{ result.evaluation }}
            </div>
          </div>

          <!-- Suggestions -->
          <div v-if="result.suggestions && result.suggestions.length">
            <h3 class="text-white font-bold mb-3 uppercase tracking-wider text-xs flex items-center">
              <span class="w-1 h-4 bg-green-500 mr-2 rounded-full"></span>
              修改建议
            </h3>
            <ul class="list-disc pl-8 space-y-2 text-gray-300">
              <li v-for="(sug, i) in result.suggestions" :key="i">{{ sug }}</li>
            </ul>
          </div>

          <!-- Improvements -->
          <div v-if="result.improvements && result.improvements.length">
            <h3 class="text-white font-bold mb-3 uppercase tracking-wider text-xs flex items-center">
              <span class="w-1 h-4 bg-yellow-500 mr-2 rounded-full"></span>
              可改进点
            </h3>
            <ul class="list-disc pl-8 space-y-2 text-gray-300">
              <li v-for="(imp, i) in result.improvements" :key="i">{{ imp }}</li>
            </ul>
          </div>

          <!-- Questions -->
          <div v-if="result.questions && result.questions.length">
            <h3 class="text-white font-bold mb-3 uppercase tracking-wider text-xs flex items-center">
              <span class="w-1 h-4 bg-red-500 mr-2 rounded-full"></span>
              疑问与思考
            </h3>
            <ul class="list-disc pl-8 space-y-2 text-gray-300">
              <li v-for="(q, i) in result.questions" :key="i">{{ q }}</li>
            </ul>
          </div>

          <!-- Full Correction -->
          <div v-if="result.correction">
            <h3 class="text-white font-bold mb-3 uppercase tracking-wider text-xs flex items-center">
              <span class="w-1 h-4 bg-blue-500 mr-2 rounded-full"></span>
              全文润色
            </h3>
            <div class="bg-gray-800/30 p-6 rounded-lg border border-gray-700/50 text-gray-300 leading-7">
              {{ result.correction }}
            </div>
          </div>

        </div>
        <div v-else class="h-full flex flex-col items-center justify-center text-gray-600 space-y-4">
          <div class="text-6xl opacity-20">📝</div>
          <p>等待输入...</p>
        </div>
      </div>
    </div>
  </div>
</template>
