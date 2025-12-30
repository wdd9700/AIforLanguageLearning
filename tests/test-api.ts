/**
 * API 测试脚本
 * 验证所有接口的健壮性
 */

const BASE_URL = 'http://localhost:3000';

import axios from 'axios';

// 辅助函数（使用 axios，便于在 Node 环境捕获错误）
async function request(method: 'GET'|'POST', path: string, body?: any, token?: string) {
  const url = `${BASE_URL}${path}`;
  try {
    const resp = await axios.request({
      url,
      method,
      data: body,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      timeout: 15000,
      validateStatus: () => true,
    });

    return { status: resp.status, data: resp.data };
  } catch (err: any) {
    // Axios 错误
    if (err.response) {
      return { status: err.response.status, data: err.response.data };
    }
    return { status: 0, error: err.message || String(err) };
  }
}

// 测试用例
async function runTests() {
  console.log('=== 开始 API 健壮性测试 ===\n');

  // 等待服务器就绪（最多等待 15 秒）
  const waitForServer = async () => {
    const start = Date.now();
    while (Date.now() - start < 15000) {
      const h = await request('GET', '/api/system/health');
      if (h.status === 200 && h.data && h.data.success) {
        console.log('Server is ready. Proceeding with tests...');
        return true;
      }
      // 等待 500ms 后重试
      await new Promise((r) => setTimeout(r, 500));
    }
    console.log('Server did not become ready within timeout; tests may fail.');
    return false;
  };

  await waitForServer();

  let accessToken = '';
  let userId = 0;

  // 1. 系统健康检查
  console.log('1. 测试系统健康检查...');
  const health = await request('GET', '/api/system/health');
  console.log(`   状态: ${health.status}`);
  console.log(`   响应:`, JSON.stringify(health.data, null, 2));
  console.log('');

  // 2. 版本信息
  console.log('2. 测试版本信息...');
  const version = await request('GET', '/api/system/version');
  console.log(`   状态: ${version.status}`);
  console.log(`   响应:`, JSON.stringify(version.data, null, 2));
  console.log('');

  // 3. 用户注册（正常情况）
  console.log('3. 测试用户注册（正常）...');
  const timestamp = Date.now();
  const register = await request('POST', '/api/auth/register', {
    username: `test_user_${timestamp}`,
    email: `test${timestamp}@example.com`,
    password: 'Test123456',
  });
  console.log(`   状态: ${register.status}`);
  if (register.data?.success) {
    accessToken = register.data.data.accessToken;
    userId = register.data.data.user.id;
    console.log(`   ✓ 注册成功，用户ID: ${userId}`);
  } else {
    console.log(`   ✗ 注册失败:`, register.data);
  }
  console.log('');

  // 4. 用户注册（弱密码）
  console.log('4. 测试用户注册（弱密码）...');
  const weakPassword = await request('POST', '/api/auth/register', {
    username: 'weak_user',
    email: 'weak@example.com',
    password: '123',
  });
  console.log(`   状态: ${weakPassword.status}`);
  console.log(`   响应:`, JSON.stringify(weakPassword.data, null, 2));
  console.log('');

  // 5. 用户注册（缺少字段）
  console.log('5. 测试用户注册（缺少字段）...');
  const missingField = await request('POST', '/api/auth/register', {
    username: 'incomplete_user',
  });
  console.log(`   状态: ${missingField.status}`);
  console.log(`   响应:`, JSON.stringify(missingField.data, null, 2));
  console.log('');

  // 6. 用户登录（正确凭据）
  console.log('6. 测试用户登录（正确凭据）...');
  const login = await request('POST', '/api/auth/login', {
    username: `test_user_${timestamp}`,
    password: 'Test123456',
  });
  console.log(`   状态: ${login.status}`);
  if (login.data?.success) {
    console.log(`   ✓ 登录成功`);
  } else {
    console.log(`   ✗ 登录失败:`, login.data);
  }
  console.log('');

  // 7. 用户登录（错误密码）
  console.log('7. 测试用户登录（错误密码）...');
  const wrongPassword = await request('POST', '/api/auth/login', {
    username: `test_user_${timestamp}`,
    password: 'WrongPassword123',
  });
  console.log(`   状态: ${wrongPassword.status}`);
  console.log(`   响应:`, JSON.stringify(wrongPassword.data, null, 2));
  console.log('');

  // 8. 获取当前用户信息（有token）
  console.log('8. 测试获取当前用户信息（有token）...');
  const me = await request('GET', '/api/auth/me', undefined, accessToken);
  console.log(`   状态: ${me.status}`);
  console.log(`   响应:`, JSON.stringify(me.data, null, 2));
  console.log('');

  // 9. 获取当前用户信息（无token）
  console.log('9. 测试获取当前用户信息（无token）...');
  const meNoToken = await request('GET', '/api/auth/me');
  console.log(`   状态: ${meNoToken.status}`);
  console.log(`   响应:`, JSON.stringify(meNoToken.data, null, 2));
  console.log('');

  // 10. 词汇查询（文本输入）
  console.log('10. 测试词汇查询（文本输入）...');
  const vocabQuery = await request('POST', '/api/query/vocabulary', {
    word: 'serendipity',
  }, accessToken);
  console.log(`   状态: ${vocabQuery.status}`);
  if (vocabQuery.data?.success) {
    console.log(`   ✓ 查询成功`);
    console.log(`   解释: ${vocabQuery.data.data.explanation?.substring(0, 100)}...`);
  } else {
    console.log(`   响应:`, JSON.stringify(vocabQuery.data, null, 2));
  }
  console.log('');

  // 11. 词汇查询（无token）
  console.log('11. 测试词汇查询（无token）...');
  const vocabNoToken = await request('POST', '/api/query/vocabulary', {
    word: 'test',
  });
  console.log(`   状态: ${vocabNoToken.status}`);
  console.log(`   响应:`, JSON.stringify(vocabNoToken.data, null, 2));
  console.log('');

  // 12. 词汇查询（缺少参数）
  console.log('12. 测试词汇查询（缺少参数）...');
  const vocabMissing = await request('POST', '/api/query/vocabulary', {}, accessToken);
  console.log(`   状态: ${vocabMissing.status}`);
  console.log(`   响应:`, JSON.stringify(vocabMissing.data, null, 2));
  console.log('');

  // 13. 学习统计
  console.log('13. 测试学习统计...');
  const stats = await request('GET', '/api/learning/stats', undefined, accessToken);
  console.log(`   状态: ${stats.status}`);
  console.log(`   响应:`, JSON.stringify(stats.data, null, 2));
  console.log('');

  // 14. 学习记录
  console.log('14. 测试学习记录...');
  const records = await request('GET', '/api/learning/records?type=vocabulary&limit=10', undefined, accessToken);
  console.log(`   状态: ${records.status}`);
  if (records.data?.success) {
    console.log(`   ✓ 获取成功，记录数: ${records.data.data.records.length}`);
  } else {
    console.log(`   响应:`, JSON.stringify(records.data, null, 2));
  }
  console.log('');

  // 15. 作文批改（正常）
  console.log('15. 测试作文批改（正常）...');
  const essay = await request('POST', '/api/essay/correct', {
    text: 'I am very happy today. Because I learning English.',
    language: 'english',
  }, accessToken);
  console.log(`   状态: ${essay.status}`);
  if (essay.data?.success) {
    console.log(`   ✓ 批改成功`);
    console.log(`   批改: ${essay.data.data.correction?.substring(0, 100)}...`);
  } else {
    console.log(`   响应:`, JSON.stringify(essay.data, null, 2));
  }
  console.log('');

  // 16. 404 测试
  console.log('16. 测试 404 错误...');
  const notFound = await request('GET', '/api/nonexistent');
  console.log(`   状态: ${notFound.status}`);
  console.log(`   响应:`, JSON.stringify(notFound.data, null, 2));
  console.log('');

  console.log('=== 测试完成 ===');
}

// 运行测试
runTests().catch(console.error);
