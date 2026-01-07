<script setup lang="ts">
/**
 * @fileoverview 语音对话视图组件 (VoiceView)
 * @description 提供语音对话的核心交互界面。
 *              包含三个主要步骤：
 *              1. 输入场景 (Input): 用户输入对话场景描述和选择目标语言。
 *              2. 审查提示词 (Review): 确认或编辑 AI 生成的系统提示词 (System Prompt)。
 *              3. 进行对话 (Active): 启动语音会话，显示水球动画 (WaterBall) 进行实时交互。
 */

import { ref, onMounted, onUnmounted } from 'vue';
import { useVoiceStore } from '../stores/voice';
import { VoiceService } from '../services/voice';
import WaterBall from '../components/WaterBall.vue';

// 引入 Voice Store 用于管理会话状态
const voiceStore = useVoiceStore();

// --- UI 状态管理 ---

/** 当前步骤: 'input' (输入) | 'review' (审查) | 'active' (进行中) */
const step = ref<'input' | 'review' | 'active'>('input');

/** 用户输入的场景描述 */
const scenarioInput = ref('');

/** 目标语言 (默认为英语) */
const targetLanguage = ref('English');

/** 生成的系统提示词 */
const generatedPrompt = ref('');

/** 是否正在生成提示词 */
const isGenerating = ref(false);

/** 是否正在启动会话 */
const isStarting = ref(false);

// --- 步骤 1: 生成提示词 ---

/**
 * 处理生成提示词
 * 
 * 调用 VoiceService.generatePrompt 根据用户输入的场景生成系统提示词。
 * 成功后进入 'review' 步骤。
 */
const handleGenerate = async () => {
  if (!scenarioInput.value.trim()) return;
  
  isGenerating.value = true;
  try {
    const prompt = await VoiceService.generatePrompt(scenarioInput.value, targetLanguage.value);
    generatedPrompt.value = prompt;
    step.value = 'review';
  } catch (e) {
    console.error(e);
    alert('生成提示词失败，请重试。');
  } finally {
    isGenerating.value = false;
  }
};

// --- 步骤 2: 确认并启动 ---

/**
 * 处理启动会话
 * 
 * 1. 调用 VoiceService.startSession 获取开场白和音频。
 * 2. 初始化 Voice Store，传入系统提示词、开场白等信息。
 * 3. 进入 'active' 步骤，显示 WaterBall 组件。
 */
const handleStart = async () => {
  isStarting.value = true;
  try {
    const result = await VoiceService.startSession(generatedPrompt.value);
    
    // 使用自定义提示词和开场白初始化 Store
    voiceStore.startCustomSession({
      systemPrompt: generatedPrompt.value,
      openingText: result.openingText,
      openingAudio: result.openingAudio,
      language: targetLanguage.value
    });
    
    step.value = 'active';
  } catch (e) {
    console.error(e);
    alert('启动会话失败。');
  } finally {
    isStarting.value = false;
  }
};

/**
 * 返回重写场景
 * 
 * 如果用户对生成的提示词不满意，可以返回第一步重新输入场景。
 */
const handleRewrite = () => {
  step.value = 'input';
};

// --- 生命周期钩子 ---

onMounted(() => {
  // 预先初始化语音服务（幂等）：注册 WS 消息处理器并尝试建立连接。
  voiceStore.init();
});

onUnmounted(() => {
  // 组件卸载时停止会话，释放资源
  voiceStore.stopSession();
});
</script>

<template>
  <div class="h-full flex flex-col relative overflow-hidden bg-gray-900">
    
    <!-- Step 1: Input Scenario -->
    <div v-if="step === 'input'" class="flex-1 flex flex-col items-center justify-center p-8 max-w-2xl mx-auto w-full z-20">
      <h1 class="text-3xl font-bold text-white mb-8">Create Your Conversation</h1>
      
      <div class="w-full space-y-6">
        <div>
          <label class="block text-gray-400 text-sm mb-2">Target Language</label>
          <div class="flex space-x-4">
            <button 
              @click="targetLanguage = 'English'"
              class="flex-1 py-3 rounded-xl border transition-all"
              :class="targetLanguage === 'English' ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'"
            >
              🇺🇸 English
            </button>
            <button 
              @click="targetLanguage = 'Japanese'"
              class="flex-1 py-3 rounded-xl border transition-all"
              :class="targetLanguage === 'Japanese' ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'"
            >
              🇯🇵 Japanese
            </button>
          </div>
        </div>

        <div>
          <label class="block text-gray-400 text-sm mb-2">Scenario Description</label>
          <textarea
            v-model="scenarioInput"
            class="w-full h-40 bg-gray-800 border border-gray-700 rounded-xl p-4 text-white focus:ring-2 focus:ring-indigo-500 outline-none resize-none"
            placeholder="e.g., Ordering a coffee in a busy Parisian cafe..."
          ></textarea>
        </div>

        <button
          @click="handleGenerate"
          :disabled="isGenerating || !scenarioInput"
          class="w-full py-4 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl text-white font-bold text-lg shadow-lg hover:shadow-indigo-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
        >
          <span v-if="isGenerating" class="animate-spin mr-2">⚡</span>
          {{ isGenerating ? 'Analyzing Scenario...' : 'Generate Prompt' }}
        </button>
      </div>
    </div>

    <!-- Step 2: Review Prompt -->
    <div v-if="step === 'review'" class="flex-1 flex flex-col items-center justify-center p-8 max-w-3xl mx-auto w-full z-20">
      <h1 class="text-2xl font-bold text-white mb-6">Review System Prompt</h1>
      
      <div class="w-full bg-gray-800 rounded-xl border border-gray-700 p-6 mb-6 relative group">
        <textarea
          v-model="generatedPrompt"
          class="w-full h-64 bg-transparent text-gray-300 font-mono text-sm outline-none resize-none custom-scrollbar"
        ></textarea>
        <div class="absolute top-2 right-2 text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity">
          Editable
        </div>
      </div>

      <div class="flex space-x-4 w-full">
        <button
          @click="handleRewrite"
          class="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl transition-colors"
        >
          Rewrite Scenario
        </button>
        <button
          @click="handleStart"
          :disabled="isStarting"
          class="flex-[2] py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold shadow-lg transition-all flex items-center justify-center"
        >
          <span v-if="isStarting" class="animate-spin mr-2">⏳</span>
          {{ isStarting ? 'Initializing Session...' : 'Confirm & Start' }}
        </button>
      </div>
    </div>

    <!-- Step 3: Active Session (WaterBall) -->
    <div v-if="step === 'active'" class="absolute inset-0 z-0">
      <div id="scene-container" class="absolute inset-0 bg-gradient-to-b from-gray-900 to-gray-800">
        <WaterBall 
          :is-listening="voiceStore.isRecording"
          :is-speaking="voiceStore.isSpeaking"
          :is-processing="voiceStore.isProcessing"
        />
      </div>

      <!-- Active UI Overlay -->
      <div class="relative z-10 h-full flex flex-col justify-between p-8 pointer-events-none">
        <!-- Header -->
        <div class="flex justify-between items-start pointer-events-auto">
          <div class="bg-black/30 backdrop-blur-md rounded-lg p-4 border border-white/10">
            <h2 class="text-xl font-bold text-white mb-1">{{ scenarioInput }}</h2>
            <div class="flex items-center space-x-2">
              <span 
                class="w-2 h-2 rounded-full"
                :class="{
                  'bg-green-500': voiceStore.statusType === 'success',
                  'bg-yellow-500': voiceStore.statusType === 'processing',
                  'bg-red-500': voiceStore.statusType === 'listening' || voiceStore.statusType === 'speaking',
                  'bg-gray-500': voiceStore.statusType === 'error'
                }"
              ></span>
              <p class="text-sm text-gray-300">{{ voiceStore.statusText }}</p>
            </div>
          </div>
          
          <button 
            @click="voiceStore.stopSession(); step = 'input'"
            class="px-4 py-2 bg-red-500/20 hover:bg-red-500/40 text-red-200 rounded-lg border border-red-500/30 transition-colors"
          >
            End Session
          </button>
        </div>

        <!-- Controls -->
        <div class="flex justify-center items-end pb-8 pointer-events-auto relative z-20">
          <button
            @click="voiceStore.toggleRecording"
            class="w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 shadow-lg hover:scale-105"
            :class="voiceStore.isRecording ? 'bg-red-500 hover:bg-red-600 shadow-red-500/50' : 'bg-indigo-500 hover:bg-indigo-600 shadow-indigo-500/50'"
          >
            <span class="text-3xl">{{ voiceStore.isRecording ? '⏹' : '🎤' }}</span>
          </button>
        </div>

        <!-- Dialogue History -->
        <div class="absolute top-24 bottom-32 left-8 w-80 pointer-events-auto overflow-y-auto space-y-4 pr-2 custom-scrollbar">
          <div 
            v-for="(msg, index) in voiceStore.currentDialogue" 
            :key="index"
            class="p-3 rounded-lg backdrop-blur-md border border-white/10 text-sm"
            :class="msg.role === 'user' ? 'bg-indigo-600/40 ml-8' : 'bg-gray-800/40 mr-8'"
          >
            <div class="text-xs opacity-50 mb-1">{{ msg.role === 'user' ? 'You' : 'AI' }}</div>
            <div class="text-white">{{ msg.content }}</div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>
