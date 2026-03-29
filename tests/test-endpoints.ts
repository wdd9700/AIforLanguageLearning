/**
 * 后端 API 端到端测试
 * 测试完整的 HTTP API 流程（四个输入入口）
 * 
 * 运行前确保：
 * 1. 后端服务器已启动（npm run dev）
 * 2. AI 服务已启动并可访问
 */

import axios, { AxiosInstance } from 'axios';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.API_URL || 'http://localhost:8012';
const ROUTE_MODE = (process.env.API_ROUTE_MODE || 'v1').toLowerCase();

const routes = {
  health: ROUTE_MODE === 'v1' ? '/health' : '/api/system/health',
  version: ROUTE_MODE === 'v1' ? '/api/system/config' : '/api/system/version',
  vocabQuery: ROUTE_MODE === 'v1' ? '/v1/vocab/lookup' : '/api/query/vocabulary',
  ocrQuery: ROUTE_MODE === 'v1' ? '/v1/vocab/lookup-ocr' : '/api/query/ocr',
  essayCorrect: ROUTE_MODE === 'v1' ? '/v1/essays/grade' : '/api/essay/correct',
  learningStats: ROUTE_MODE === 'v1' ? '/v1/learning/stats' : '/api/learning/stats',
};

// 创建 axios 实例
const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 180000, // Increased timeout for large audio files
  validateStatus: () => true, // 不自动抛出错误，方便测试各种状态码
});

// 测试结果收集
const results: { name: string; status: 'PASS' | 'FAIL'; message: string }[] = [];
let authToken: string = '';
let userId: string = '';

function logTest(name: string, pass: boolean, message: string) {
  results.push({ name, status: pass ? 'PASS' : 'FAIL', message });
  const icon = pass ? '✅' : '❌';
  console.log(`${icon} ${name}: ${message}`);
}

/**
 * 等待服务器就绪
 */
async function waitForServer(maxAttempts = 30, interval = 1000): Promise<boolean> {
  console.log('⏳ Waiting for server to be ready...');
  
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const response = await api.get(routes.health);
      if (response.status === 200) {
        console.log('✅ Server is ready!\n');
        return true;
      }
    } catch (error) {
      // 继续等待
    }
    
    await new Promise((resolve) => setTimeout(resolve, interval));
    process.stdout.write('.');
  }
  
  console.log('\n❌ Server did not become ready in time');
  return false;
}

/**
 * 1. 测试系统健康检查
 */
async function testSystemHealth() {
  console.log('\n📊 Testing System Endpoints...');
  
  const healthRes = await api.get(routes.health);
  logTest(
    'System Health',
    healthRes.status === 200 && (ROUTE_MODE === 'v1' ? !!healthRes.data?.ok : !!healthRes.data?.success),
    healthRes.status === 200 ? 'System healthy' : `Status ${healthRes.status}`
  );

  const versionRes = await api.get(routes.version);
  logTest(
    'System Version',
    versionRes.status === 200,
    versionRes.status === 200 ? `Version: ${versionRes.data.version}` : `Status ${versionRes.status}`
  );
}

/**
 * 2. 测试用户认证流程
 */
async function testAuthentication() {
  console.log('\n🔐 Testing Authentication...');

  // 注册新用户
  const username = `testuser_${Date.now()}`;
  const password = 'TestPassword123!';

  const registerRes = await api.post('/api/auth/register', {
    username,
    password,
    email: `${username}@test.com`,
  });

  if (registerRes.status === 201 && registerRes.data.data?.accessToken) {
    logTest('User Registration', true, `User created: ${username}`);
    authToken = registerRes.data.data.accessToken;
    userId = registerRes.data.data.user.id;
  } else {
    logTest('User Registration', false, `Status ${registerRes.status}: ${registerRes.data.message}`);
    return false;
  }

  // 登录
  const loginRes = await api.post('/api/auth/login', {
    username,
    password,
  });

  logTest(
    'User Login',
    loginRes.status === 200 && loginRes.data.data?.accessToken,
    loginRes.status === 200 ? 'Login successful' : `Status ${loginRes.status}`
  );

  // 获取当前用户信息
  const meRes = await api.get('/api/auth/me', {
    headers: { Authorization: `Bearer ${authToken}` },
  });

  logTest(
    'Get Current User',
    meRes.status === 200 && meRes.data.data?.username === username,
    meRes.status === 200 ? `User: ${meRes.data.data.username}` : `Status ${meRes.status}`
  );

  return true;
}

/**
 * 3. 测试四个输入入口 - 文本输入（词汇查询）
 */
async function testVocabularyQuery() {
  console.log('\n📝 Testing Entry 1: Text Input (Vocabulary Query)...');

  const response = await api.post(
    routes.vocabQuery,
    ROUTE_MODE === 'v1'
      ? {
          term: 'ephemeral',
          source: 'manual',
        }
      : {
          word: 'ephemeral',
          context: 'The beauty of cherry blossoms is ephemeral.',
          sourceLanguage: 'en',
          targetLanguage: 'zh',
        },
    {
      headers: { Authorization: `Bearer ${authToken}` },
    }
  );

  const data = response.data;
  if (response.status === 200) {
    const explanation = ROUTE_MODE === 'v1'
      ? String(data?.definition || '')
      : String(data?.data?.meaning || data?.data?.definition || '');
    logTest(
      'Vocabulary Query',
      !!explanation,
      `Explanation/Definition: "${explanation.substring(0, 50)}..."`
    );
    console.log('   Full response:', explanation);
  } else {
    console.log('   Full Response Data:', JSON.stringify(response.data, null, 2));
    logTest(
      'Vocabulary Query',
      false,
      `Status ${response.status}: ${response.data.message || 'No explanation/definition'}`
    );
  }
}

/**
 * 4. 测试四个输入入口 - 截图 OCR
 */
async function testOCRQuery() {
  console.log('\n🖼️  Testing Entry 2: Screenshot OCR...');

  // 检查测试图片
  const testImagePath = path.join(__dirname, 'test-image.png');
  if (!fs.existsSync(testImagePath)) {
    logTest('OCR Query', false, 'Test image not found (backend/test-image.png)');
    return;
  }

  const imageBuffer = fs.readFileSync(testImagePath);
  const imageBase64 = imageBuffer.toString('base64');

  const response = await api.post(
    routes.ocrQuery,
    ROUTE_MODE === 'v1'
      ? {
          image: imageBase64,
          language: 'english',
        }
      : {
          image: imageBase64,
          sourceLanguage: 'en',
          targetLanguage: 'zh',
        },
    {
      headers: { Authorization: `Bearer ${authToken}` },
    }
  );

  if (response.status === 200) {
    const text = ROUTE_MODE === 'v1'
      ? (response.data?.ocr_text || response.data?.term || '')
      : (response.data?.data?.text || response.data?.data?.detectedText || response.data?.data?.ocrText || '');
    logTest('OCR Query', true, `OCR text: "${text.substring(0, 50)}..."`);
    if (ROUTE_MODE !== 'v1' && response.data?.data?.explanation) {
      console.log('   Explanation:', JSON.stringify(response.data.data.explanation).substring(0, 100));
    }
  } else {
    console.log('   Full Response Data:', JSON.stringify(response.data, null, 2));
    logTest('OCR Query', false, `Status ${response.status}: ${response.data.message || 'No OCR result'}`);
  }
}

/**
 * 5. 测试四个输入入口 - 选中文本
 */
async function testSelectedTextQuery() {
  console.log('\n🖱️  Testing Entry 3: Selected Text...');

  const response = await api.post(
    '/api/query/selected',
    {
      text: 'The quintessential example of Renaissance architecture.',
      sourceLanguage: 'en',
      targetLanguage: 'zh',
    },
    {
      headers: { Authorization: `Bearer ${authToken}` },
    }
  );

  const data = response.data.data;
  if (response.status === 200 && (data?.explanation || data?.definition)) {
    let explanation = data.explanation || data.definition;
    if (typeof explanation === 'object') {
        explanation = JSON.stringify(explanation);
    }
    logTest(
      'Selected Text Query',
      true,
      `Explanation: "${String(explanation).substring(0, 50)}..."`
    );
  } else {
    console.log('   Full Response Data:', JSON.stringify(response.data, null, 2));
    logTest(
      'Selected Text Query',
      false,
      `Status ${response.status}: ${response.data.message || 'No explanation'}`
    );
  }
}

/**
 * 6. 测试四个输入入口 - 语音输入
 */
async function testVoiceQuery() {
  console.log('\n🎤 Testing Entry 4: Voice Input...');

  const testAudioPath = path.join(__dirname, 'test-audio.wav');
  if (!fs.existsSync(testAudioPath)) {
    logTest('Voice Query', false, 'Test audio not found (backend/test-audio.wav)');
    return;
  }

  const audioBuffer = fs.readFileSync(testAudioPath);
  const audioBase64 = audioBuffer.toString('base64');

  const response = await api.post(
    '/api/query/voice',
    {
      audio: audioBase64,
      sourceLanguage: 'en',
      targetLanguage: 'zh',
    },
    {
      headers: { Authorization: `Bearer ${authToken}` },
    }
  );

  if (response.status === 200 && (response.data.data?.transcription || response.data.data?.detectedText)) {
    const text = response.data.data.transcription || response.data.data.detectedText;
    logTest(
      'Voice Query',
      true,
      `Transcription: "${text.substring(0, 50)}..."`
    );
    if (response.data.data.explanation) {
      console.log('   Explanation:', JSON.stringify(response.data.data.explanation).substring(0, 100));
    }
  } else if (response.status === 400 && response.data.error?.code === 'ASR_NO_TEXT') {
    logTest(
      'Voice Query',
      true,
      'ASR Service working (No text detected in dummy audio)'
    );
  } else {
    console.log('   Full Response Data:', JSON.stringify(response.data, null, 2));
    logTest(
      'Voice Query',
      false,
      `Status ${response.status}: ${response.data.message || 'No transcription'}`
    );
  }
}

/**
 * 7. 测试作文批改
 */
async function testEssayCorrection() {
  console.log('\n📄 Testing Essay Correction...');

  const essay = `This is a test essay with some grammer mistakes. 
I want to improving my English writing skill. 
The weather is very nice today, I go to park.`;

  const response = await api.post(
    routes.essayCorrect,
    ROUTE_MODE === 'v1'
      ? {
          ocr_text: essay,
          language: 'en',
        }
      : {
          text: essay,
          language: 'en',
          targetLanguage: 'zh',
        },
    {
      headers: { Authorization: `Bearer ${authToken}` },
    }
  );

  const data = response.data;
  const corrections = ROUTE_MODE === 'v1'
    ? (data?.result?.errors || data?.result?.suggestions || [])
    : (data?.data?.corrections || data?.data?.details || []);

  if (response.status === 200) {
    logTest(
      'Essay Correction',
      true,
      `Found ${Array.isArray(corrections) ? corrections.length : 0} corrections`
    );
    console.log('   Corrections:', JSON.stringify((Array.isArray(corrections) ? corrections : []).slice(0, 2), null, 2));
  } else {
    console.log('   Full Response Data:', JSON.stringify(response.data, null, 2));
    logTest(
      'Essay Correction',
      false,
      `Status ${response.status}: ${response.data.message || 'No corrections'}`
    );
  }
}

/**
 * 8. 测试学习记录
 */
async function testLearningRecords() {
  console.log('\n📚 Testing Learning Records...');

  // 获取学习记录
  const recordsRes = await api.get('/api/learning/records', {
    headers: { Authorization: `Bearer ${authToken}` },
  });

  logTest(
    'Get Learning Records',
    recordsRes.status === 200,
    recordsRes.status === 200
      ? `Found ${recordsRes.data.data?.records?.length || 0} records`
      : `Status ${recordsRes.status}`
  );

  // 获取学习统计
  const statsRes = await api.get(routes.learningStats, {
    headers: { Authorization: `Bearer ${authToken}` },
  });

  logTest(
    'Get Learning Stats',
    statsRes.status === 200,
    statsRes.status === 200 ? 'Stats retrieved' : `Status ${statsRes.status}`
  );

  if (statsRes.status === 200) {
    const statsData = ROUTE_MODE === 'v1' ? statsRes.data : statsRes.data?.data;
    console.log('   Stats:', JSON.stringify(statsData, null, 2));
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

  console.log(`Total tests: ${results.length}`);
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);

  if (failed > 0) {
    console.log('\n❌ Failed tests:');
    results
      .filter((r) => r.status === 'FAIL')
      .forEach((r) => {
        console.log(`  - ${r.name}: ${r.message}`);
      });
  }

  console.log('\n' + '='.repeat(60));

  return failed > 0 ? 1 : 0;
}

/**
 * 主测试流程
 */
async function runTests() {
  console.log('🚀 Starting Backend API Integration Tests');
  console.log(`API Base URL: ${BASE_URL}\n`);

  // 等待服务器就绪
  const serverReady = await waitForServer();
  if (!serverReady) {
    console.error('❌ Server is not ready. Please start the backend server first.');
    process.exit(1);
  }

  // 运行测试
  await testSystemHealth();
  
  const authSuccess = await testAuthentication();
  if (!authSuccess) {
    console.error('❌ Authentication failed. Cannot continue with protected endpoint tests.');
    process.exit(1);
  }

  // 测试四个输入入口
  await testVocabularyQuery();
  await testOCRQuery();
  await testSelectedTextQuery();
  await testVoiceQuery();

  // 测试其他功能
  await testEssayCorrection();
  await testLearningRecords();

  const exitCode = printSummary();
  process.exit(exitCode);
}

// 运行测试
runTests().catch((error) => {
  console.error('Fatal error during tests:', error);
  process.exit(1);
});
