/**
 * AI 服务状态检查工具
 * 快速检查所有 AI 服务的运行状态
 */

import axios from 'axios';

const config = {
  llm: {
    endpoint: process.env.LLM_ENDPOINT || 'http://localhost:1234/v1/chat/completions',
    healthCheck: 'http://localhost:1234/v1/models',
    name: 'LM Studio',
  },
  ocr: {
    endpoint: process.env.OCR_ENDPOINT || 'http://localhost:5001/ocr',
    healthCheck: 'http://localhost:5001/health',
    name: 'SuryaOCR',
  },
  tts: {
    endpoint: process.env.TTS_ENDPOINT || 'http://localhost:5003/synthesize',
    healthCheck: 'http://localhost:5003/health',
    name: 'CosyVoice TTS',
  },
  asr: {
    endpoint: process.env.ASR_ENDPOINT || 'http://localhost:5002/transcribe',
    healthCheck: 'http://localhost:5002/health',
    name: 'Whisper ASR',
  },
};

interface ServiceCheck {
  name: string;
  url: string;
  status: 'running' | 'error' | 'no-model';
  message: string;
  details?: any;
}

async function checkService(
  name: string,
  endpoint: string,
  healthCheck: string
): Promise<ServiceCheck> {
  try {
    // 先尝试健康检查端点
    const response = await axios.get(healthCheck, { timeout: 3000 });
    return {
      name,
      url: endpoint,
      status: 'running',
      message: '✅ Service is running',
      details: response.data,
    };
  } catch (healthError: any) {
    // 健康检查失败，尝试直接访问服务端点
    try {
      if (name === 'LM Studio') {
        // LM Studio 特殊检查：查询模型列表
        const modelsResponse = await axios.get('http://localhost:1234/v1/models', { timeout: 3000 });
        const models = modelsResponse.data?.data || [];
        
        if (models.length === 0) {
          return {
            name,
            url: endpoint,
            status: 'no-model',
            message: '⚠️  LM Studio is running but NO MODEL loaded',
            details: { hint: 'Load a model in LM Studio UI or use "lms load <model-name>"' },
          };
        }
        
        return {
          name,
          url: endpoint,
          status: 'running',
          message: `✅ Service is running with ${models.length} model(s)`,
          details: { models: models.map((m: any) => m.id) },
        };
      }
      
      // 其他服务：尝试访问基础端点
      const baseUrl = endpoint.replace(/\/[^/]+$/, '');
      const response = await axios.get(baseUrl, { timeout: 3000 });
      
      return {
        name,
        url: endpoint,
        status: 'running',
        message: '✅ Service is running (no health endpoint)',
        details: null,
      };
    } catch (error: any) {
      if (error.code === 'ECONNREFUSED') {
        return {
          name,
          url: endpoint,
          status: 'error',
          message: `❌ Service NOT running (connection refused)`,
          details: { hint: `Start the service on ${endpoint}` },
        };
      }
      
      return {
        name,
        url: endpoint,
        status: 'error',
        message: `❌ Service error: ${error.message}`,
        details: { code: error.code, status: error.response?.status },
      };
    }
  }
}

async function checkAllServices() {
  console.log('🔍 Checking AI Services Status...\n');
  console.log('=' .repeat(70));

  const checks: ServiceCheck[] = [];

  for (const [key, service] of Object.entries(config)) {
    const result = await checkService(service.name, service.endpoint, service.healthCheck);
    checks.push(result);
  }

  // 打印结果
  for (const check of checks) {
    console.log(`\n📦 ${check.name}`);
    console.log(`   Endpoint: ${check.url}`);
    console.log(`   Status:   ${check.message}`);
    
    if (check.details) {
      console.log(`   Details:  ${JSON.stringify(check.details, null, 2).replace(/\n/g, '\n             ')}`);
    }
  }

  console.log('\n' + '='.repeat(70));
  
  // 统计
  const running = checks.filter(c => c.status === 'running').length;
  const errors = checks.filter(c => c.status === 'error').length;
  const noModel = checks.filter(c => c.status === 'no-model').length;
  
  console.log('\n📊 Summary:');
  console.log(`   ✅ Running: ${running}`);
  console.log(`   ⚠️  No Model: ${noModel}`);
  console.log(`   ❌ Not Running: ${errors}`);
  
  // 提供建议
  if (errors > 0 || noModel > 0) {
    console.log('\n💡 Next Steps:');
    
    for (const check of checks) {
      if (check.status === 'error') {
        console.log(`   • Start ${check.name}: ${check.details?.hint || 'See service documentation'}`);
      } else if (check.status === 'no-model') {
        console.log(`   • ${check.details?.hint || 'Load a model'}`);
      }
    }
  } else {
    console.log('\n✨ All services are ready! You can now run the tests.');
  }
  
  console.log('\n');
  
  return errors === 0 && noModel === 0;
}

// 运行检查
checkAllServices()
  .then(allReady => {
    process.exit(allReady ? 0 : 1);
  })
  .catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
