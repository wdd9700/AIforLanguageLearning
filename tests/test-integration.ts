/**
 * 快速测试脚本 - 测试集成后的服务
 * 测试 LLM 模型管理、ASR Faster-Whisper、TTS GPU
 */

import { ServiceManager } from '../backend/src/managers/service-manager';
import * as fs from 'fs';
import * as path from 'path';

async function main() {
  console.log('=== 开始测试集成后的服务 ===\n');
  
  const serviceManager = new ServiceManager();
  await serviceManager.initialize();
  
  // 1. 测试 LLM 模型管理
  console.log('--- 1. 测试 LLM 模型管理 ---');
  
  try {
    console.log('1.1 列出所有 LLM 模型...');
    const listResult = await serviceManager.listLLMModels();
    
    if (listResult.ok && listResult.models) {
      console.log(`✓ 成功列出 ${listResult.models.length} 个模型:`);
      listResult.models.slice(0, 5).forEach((model: any) => {
        console.log(`  - ${model.identifier || model.path} (${model.loaded ? '已加载' : '未加载'})`);
      });
    } else {
      console.log(`✗ 列出模型失败: ${listResult.error}`);
    }
    
    console.log('\n1.2 获取已加载的模型...');
    const loadedResult = await serviceManager.getLoadedLLMModels();
    
    if (loadedResult.ok && loadedResult.models) {
      console.log(`✓ 已加载 ${loadedResult.models.length} 个模型`);
      loadedResult.models.forEach((model: any) => {
        console.log(`  - ${model.identifier || model.path}`);
      });
    }
    
  } catch (error: any) {
    console.error('✗ LLM 模型管理测试失败:', error.message);
  }
  
  // 2. 测试 ASR Faster-Whisper
  console.log('\n--- 2. 测试 ASR Faster-Whisper ---');
  
  try {
    const testAudioPath = path.join(__dirname, '../testresources/ASRtest.wav');
    
    if (!fs.existsSync(testAudioPath)) {
      console.log('✗ 测试音频文件不存在:', testAudioPath);
    } else {
      console.log('2.1 加载测试音频...');
      const audioBuffer = fs.readFileSync(testAudioPath);
      console.log(`✓ 音频大小: ${(audioBuffer.length / 1024 / 1024).toFixed(2)} MB`);
      
      console.log('2.2 开始 ASR 转录 (这可能需要 1-2 分钟)...');
      const startTime = Date.now();
      
      const asrResult = await serviceManager.invokeASR(audioBuffer, {
        language: 'en',
        model: 'small'
      });
      
      const elapsed = (Date.now() - startTime) / 1000;
      
      console.log(`✓ ASR 转录完成 (${elapsed.toFixed(2)}s):`);
      console.log(`  - 文本长度: ${asrResult.text.length} 字符`);
      console.log(`  - 语言: ${asrResult.language}`);
      console.log(`  - 音频时长: ${asrResult.duration?.toFixed(2)}s`);
      console.log(`  - 加载时间: ${asrResult.loadTime?.toFixed(2)}s`);
      console.log(`  - 转录时间: ${asrResult.transcribeTime?.toFixed(2)}s`);
      console.log(`  - RTF: ${asrResult.rtf?.toFixed(3)}x`);
      console.log(`  - 文本预览: ${asrResult.text.substring(0, 100)}...`);
    }
  } catch (error: any) {
    console.error('✗ ASR 测试失败:', error.message);
  }
  
  // 3. 测试 LLM 调用
  console.log('\n--- 3. 测试 LLM 调用 ---');
  
  try {
    console.log('3.1 发送测试提示...');
    const llmResult = await serviceManager.invokeLLM({
      prompt: '你好,请简单介绍一下你自己。',
      maxTokens: 100,
      temperature: 0.7,
    });
    
    console.log('✓ LLM 响应:');
    console.log(`  ${llmResult.response}`);
    if (llmResult.tokenUsage) {
      console.log(`  Token 使用: ${JSON.stringify(llmResult.tokenUsage)}`);
    }
  } catch (error: any) {
    console.error('✗ LLM 测试失败:', error.message);
  }
  
  // 4. 测试 TTS (可选,需要较长时间)
  console.log('\n--- 4. 测试 TTS (跳过,避免长时间等待) ---');
  console.log('提示: 使用 npm run test:tts-only 单独测试 TTS');
  
  console.log('\n=== 测试完成 ===');
  process.exit(0);
}

main().catch((error) => {
  console.error('测试失败:', error);
  process.exit(1);
});
