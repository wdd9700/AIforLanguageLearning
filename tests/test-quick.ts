/**
 * 快速测试各个服务的实际调用
 */

import { ServiceManager } from '../backend/src/managers/service-manager';
import * as fs from 'fs';
import * as path from 'path';

async function testOCR() {
  console.log('\n📸 Testing OCR Service...');
  
  // 创建一个简单的测试图片（白底黑字 "Hello World"）
  // 这里我们需要一个真实的图片，暂时跳过
  console.log('   ⏭️  Skipped (need test image)');
  console.log('   💡 Create backend/test-image.png with some text to test');
}

async function testLLM() {
  console.log('\n💬 Testing LLM Service...');
  
  const sm = new ServiceManager();
  await sm.initialize();
  
  try {
    const result = await sm.invokeLLM({
      prompt: 'Explain the word "ephemeral" in one sentence.',
      maxTokens: 50,
    });
    
    console.log('   ✅ LLM Response:', result.response.substring(0, 100) + '...');
    console.log('   📊 Token usage:', result.tokenUsage);
  } catch (error: any) {
    console.log('   ❌ LLM Error:', error.message);
    console.log('   💡 Make sure LM Studio is running on http://localhost:1234');
  }
}

async function testTTS() {
  console.log('\n🔊 Testing TTS Service...');
  
  const sm = new ServiceManager();
  await sm.initialize();
  
  try {
    const result = await sm.invokeTTS('Hello, this is a test.');
    
    const outputPath = path.join(__dirname, 'test-tts-output.wav');
    fs.writeFileSync(outputPath, result.audio);
    
    console.log('   ✅ TTS completed');
    console.log('   📊 Audio size:', result.audio.length, 'bytes');
    console.log('   💾 Saved to:', outputPath);
  } catch (error: any) {
    console.log('   ❌ Error:', error.message);
  }
}

async function testASR() {
  console.log('\n🎤 Testing ASR Service...');
  console.log('   ⏭️  Skipped (need test audio)');
  console.log('   💡 Create backend/test-audio.wav to test');
}

async function main() {
  console.log('🧪 Quick Service Integration Tests\n');
  console.log('='.repeat(60));
  
  await testLLM();
  await testOCR();
  await testTTS();
  await testASR();
  
  console.log('\n' + '='.repeat(60));
  console.log('✨ Tests completed!');
  console.log('\n💡 Next steps:');
  console.log('   1. Add test-image.png to test OCR');
  console.log('   2. Add test-audio.wav to test ASR');
  console.log('   3. Run full API tests: npm run test:endpoints');
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
