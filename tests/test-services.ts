/**
 * AI 服务集成测试
 * 直接测试 ServiceManager 对各 AI 服务的调用
 * 
 * 运行前确保：
 * 1. LM Studio 已启动并加载模型（默认 http://localhost:1234）
 * 2. SuryaOCR 服务已启动（默认 http://localhost:5001）
 * 3. CosyVoice TTS 服务已启动（默认 http://localhost:5003）
 * 4. Whisper ASR 服务已启动（可选，默认 http://localhost:5002）
 */

import axios from 'axios';
import * as fs from 'fs';
import * as path from 'path';

// 测试配置
const config = {
  llm: {
    endpoint: process.env.LLM_ENDPOINT || 'http://localhost:1234/v1/chat/completions',
    model: process.env.LLM_MODEL || 'qwen2.5-7b-instruct',
  },
  ocr: {
    endpoint: process.env.OCR_ENDPOINT || 'http://localhost:5001/ocr',
  },
  tts: {
    endpoint: process.env.TTS_ENDPOINT || 'http://localhost:5003/synthesize',
  },
  asr: {
    endpoint: process.env.ASR_ENDPOINT || 'http://localhost:5002/transcribe',
  },
};

// 测试结果收集
const results: { name: string; status: 'PASS' | 'FAIL' | 'SKIP'; message: string; time?: number }[] = [];

function logTest(name: string, status: 'PASS' | 'FAIL' | 'SKIP', message: string, time?: number) {
  results.push({ name, status, message, time });
  const icon = status === 'PASS' ? '✅' : status === 'FAIL' ? '❌' : '⏭️';
  console.log(`${icon} ${name}: ${message}${time ? ` (${time}ms)` : ''}`);
}

/**
 * 测试 LM Studio LLM 服务
 */
async function testLLMService() {
  console.log('\n📚 Testing LLM Service (LM Studio)...');
  const testName = 'LLM Service';
  
  try {
    const startTime = Date.now();
    
    // 1. 健康检查（尝试简单调用）
    const healthResponse = await axios.post(
      config.llm.endpoint,
      {
        model: config.llm.model,
        messages: [{ role: 'user', content: 'Hello, are you working?' }],
        max_tokens: 50,
        temperature: 0.7,
        stream: false,
      },
      { timeout: 10000 }
    );

    const elapsed = Date.now() - startTime;

    if (healthResponse.data?.choices?.[0]?.message?.content) {
      logTest(
        testName + ' - Health Check',
        'PASS',
        `Response: "${healthResponse.data.choices[0].message.content.substring(0, 50)}..."`,
        elapsed
      );
    } else {
      logTest(testName + ' - Health Check', 'FAIL', 'Invalid response format');
      return;
    }

    // 2. 测试实际任务（词汇查询）
    const startTime2 = Date.now();
    const vocabResponse = await axios.post(
      config.llm.endpoint,
      {
        model: config.llm.model,
        messages: [
          {
            role: 'system',
            content: 'You are a language learning assistant. Provide word definitions, usage examples, and translations.',
          },
          {
            role: 'user',
            content: 'Please explain the word "ephemeral" with definition, example sentence, and Chinese translation.',
          },
        ],
        max_tokens: 200,
        temperature: 0.7,
      },
      { timeout: 15000 }
    );

    const elapsed2 = Date.now() - startTime2;
    
    if (vocabResponse.data?.choices?.[0]?.message?.content) {
      logTest(
        testName + ' - Vocabulary Query',
        'PASS',
        `Generated ${vocabResponse.data.choices[0].message.content.length} chars`,
        elapsed2
      );
      console.log('   Sample output:', vocabResponse.data.choices[0].message.content.substring(0, 100) + '...');
      
      // 显示 token 使用情况
      if (vocabResponse.data.usage) {
        console.log('   Token usage:', vocabResponse.data.usage);
      }
    } else {
      logTest(testName + ' - Vocabulary Query', 'FAIL', 'Invalid response');
    }

  } catch (error: any) {
    let errorMsg = error.message;
    if (error.code === 'ECONNREFUSED') {
      errorMsg = `Connection refused. Is LM Studio running on ${config.llm.endpoint}?`;
    } else if (error.response) {
      errorMsg = `HTTP ${error.response.status}: ${JSON.stringify(error.response.data)}`;
    }
    logTest(testName, 'FAIL', errorMsg);
  }
}

/**
 * 测试 SuryaOCR 服务
 */
async function testOCRService() {
  console.log('\n🖼️  Testing OCR Service (SuryaOCR)...');
  const testName = 'OCR Service';

  try {
    // 创建一个测试图片（简单的 base64 编码文本图片，或使用现有图片）
    // 这里需要用户提供一个实际的测试图片
    // 示例：读取本地测试图片
    const testImagePath = path.join(__dirname, 'test-image.png');
    
    if (!fs.existsSync(testImagePath)) {
      logTest(
        testName,
        'SKIP',
        'Test image not found. Please create backend/test-image.png with sample text.'
      );
      return;
    }

    const imageBuffer = fs.readFileSync(testImagePath);
    const imageBase64 = imageBuffer.toString('base64');

    const startTime = Date.now();
    
    // 根据 SuryaOCR 实际 API 调整请求格式
    const response = await axios.post(
      config.ocr.endpoint,
      {
        image: imageBase64,
        // 可能需要的其他参数
      },
      { 
        timeout: 30000,
        headers: { 'Content-Type': 'application/json' },
      }
    );

    const elapsed = Date.now() - startTime;

    // 根据实际响应格式调整
    const text = response.data.text || response.data.result || '';
    const confidence = response.data.confidence || response.data.score || 0;

    if (text) {
      logTest(
        testName,
        'PASS',
        `Extracted text: "${text.substring(0, 50)}..." (confidence: ${confidence})`,
        elapsed
      );
    } else {
      logTest(testName, 'FAIL', 'No text extracted from image');
    }

  } catch (error: any) {
    let errorMsg = error.message;
    if (error.code === 'ECONNREFUSED') {
      errorMsg = `Connection refused. Is SuryaOCR running on ${config.ocr.endpoint}?`;
    } else if (error.response) {
      errorMsg = `HTTP ${error.response.status}: ${JSON.stringify(error.response.data)}`;
    }
    logTest(testName, 'FAIL', errorMsg);
  }
}

/**
 * 测试 CosyVoice TTS 服务
 */
async function testTTSService() {
  console.log('\n🔊 Testing TTS Service (CosyVoice)...');
  const testName = 'TTS Service';

  try {
    const testText = 'Hello, this is a test of the text to speech service.';
    const startTime = Date.now();

    // 根据 CosyVoice 实际 API 调整请求格式
    const response = await axios.post(
      config.tts.endpoint,
      {
        text: testText,
        voice: 'default', // 根据实际支持的语音调整
        speed: 1.0,
      },
      {
        timeout: 15000,
        responseType: 'arraybuffer',
      }
    );

    const elapsed = Date.now() - startTime;
    const audioSize = response.data.byteLength;

    if (audioSize > 0) {
      logTest(
        testName,
        'PASS',
        `Generated ${audioSize} bytes audio (${(audioSize / 1024).toFixed(2)} KB)`,
        elapsed
      );

      // 可选：保存音频文件用于验证
      const outputPath = path.join(__dirname, 'test-output.wav');
      fs.writeFileSync(outputPath, Buffer.from(response.data));
      console.log(`   Audio saved to: ${outputPath}`);
    } else {
      logTest(testName, 'FAIL', 'Generated empty audio');
    }

  } catch (error: any) {
    let errorMsg = error.message;
    if (error.code === 'ECONNREFUSED') {
      errorMsg = `Connection refused. Is CosyVoice running on ${config.tts.endpoint}?`;
    } else if (error.response) {
      errorMsg = `HTTP ${error.response.status}`;
    }
    logTest(testName, 'FAIL', errorMsg);
  }
}

/**
 * 测试 Whisper ASR 服务（可选）
 */
async function testASRService() {
  console.log('\n🎤 Testing ASR Service (Whisper) - Optional...');
  const testName = 'ASR Service';

  try {
    // 需要一个测试音频文件
    const testAudioPath = path.join(__dirname, 'test-audio.wav');
    
    if (!fs.existsSync(testAudioPath)) {
      logTest(
        testName,
        'SKIP',
        'Test audio not found. Please create backend/test-audio.wav for ASR testing.'
      );
      return;
    }

    const audioBuffer = fs.readFileSync(testAudioPath);
    const startTime = Date.now();

    // 使用 FormData 上传音频
    const FormData = require('form-data');
    const formData = new FormData();
    formData.append('audio', audioBuffer, 'test-audio.wav');

    const response = await axios.post(config.asr.endpoint, formData, {
      timeout: 60000,
      headers: formData.getHeaders(),
    });

    const elapsed = Date.now() - startTime;
    const text = response.data.text || '';

    if (text) {
      logTest(testName, 'PASS', `Transcribed: "${text.substring(0, 50)}..."`, elapsed);
    } else {
      logTest(testName, 'FAIL', 'No transcription result');
    }

  } catch (error: any) {
    let errorMsg = error.message;
    if (error.code === 'ECONNREFUSED') {
      errorMsg = `Connection refused. Is Whisper running on ${config.asr.endpoint}?`;
    } else if (error.response) {
      errorMsg = `HTTP ${error.response.status}: ${JSON.stringify(error.response.data)}`;
    }
    logTest(testName, 'FAIL', errorMsg);
  }
}

/**
 * 打印测试摘要
 */
function printSummary() {
  console.log('\n' + '='.repeat(60));
  console.log('📊 Test Summary');
  console.log('='.repeat(60));

  const passed = results.filter((r) => r.status === 'PASS').length;
  const failed = results.filter((r) => r.status === 'FAIL').length;
  const skipped = results.filter((r) => r.status === 'SKIP').length;

  console.log(`Total tests: ${results.length}`);
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);
  console.log(`⏭️  Skipped: ${skipped}`);

  if (failed > 0) {
    console.log('\n❌ Failed tests:');
    results
      .filter((r) => r.status === 'FAIL')
      .forEach((r) => {
        console.log(`  - ${r.name}: ${r.message}`);
      });
  }

  console.log('\n' + '='.repeat(60));
  
  // 返回退出码
  return failed > 0 ? 1 : 0;
}

/**
 * 主测试流程
 */
async function runTests() {
  console.log('🚀 Starting AI Services Integration Tests\n');
  console.log('Configuration:');
  console.log(`  LLM:  ${config.llm.endpoint} (model: ${config.llm.model})`);
  console.log(`  OCR:  ${config.ocr.endpoint}`);
  console.log(`  TTS:  ${config.tts.endpoint}`);
  console.log(`  ASR:  ${config.asr.endpoint}`);

  await testLLMService();
  await testOCRService();
  await testTTSService();
  await testASRService();

  const exitCode = printSummary();
  process.exit(exitCode);
}

// 运行测试
runTests().catch((error) => {
  console.error('Fatal error during tests:', error);
  process.exit(1);
});
