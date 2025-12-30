
import { ServiceManager } from '../src/managers/service-manager';
import { createLogger } from '../src/utils/logger';
import { config } from '../src/config/env';

const logger = createLogger('RealInteractionTest');

async function testRealInteraction() {
  console.log('--- Starting Real LLM Interaction Test ---');

  // 1. Initialize Service Manager
  const serviceManager = new ServiceManager();
  
  // We only need LLM and Prompt for this test, but initialize all to be safe/standard
  // Mocking other services to avoid startup overhead if possible? 
  // No, let's just init LLM specifically to save time/resources if we can, 
  // but ServiceManager.initialize() does all.
  // Let's just init LLM manually for this test script to be lightweight.
  
  console.log('Initializing LLM Service...');
  await serviceManager.llm.initialize();
  
  // Wait a bit for the probe to finish and populate effectiveModels
  console.log('Waiting for model probe...');
  await new Promise(resolve => setTimeout(resolve, 2000));

  // 2. Inspect Model Routing
  console.log('\n--- Model Routing Status ---');
  // Access private property via any cast for debugging
  const effectiveModels = (serviceManager.llm as any).effectiveModels;
  console.log('Effective Models Mapping:', effectiveModels);

  const analysisModel = effectiveModels.get('analysis');
  const expansionModel = effectiveModels.get('prompt_expansion');
  
  console.log(`\n[Analysis Task] Mapped Model: ${analysisModel}`);
  console.log(`[Expansion Task] Mapped Model: ${expansionModel}`);

  if (!analysisModel || !expansionModel) {
    console.error('❌ CRITICAL: Target models not found in effective configuration!');
    console.log('Configured Analysis Model:', config.services.llm.models.analysis);
    console.log('Configured Expansion Model:', config.services.llm.models.prompt_expansion);
    // We continue to try invoke, but it might fail or use fallback
  }

  // 3. Test Prompt Expansion (Thinking Model)
  console.log('\n--- Testing Prompt Expansion (Thinking Model) ---');
  try {
    const scenario = "I want to practice ordering food in a French restaurant.";
    const targetLang = "French";
    
    console.log(`Scenario: ${scenario}`);
    console.log('Rendering prompt...');
    const prompt = await serviceManager.prompt.render('analysis/prompt_expansion', {
      scenario,
      targetLang
    });
    
    console.log('Invoking LLM (Task: prompt_expansion)...');
    const start = Date.now();
    const response = await serviceManager.llm.invoke({
      prompt,
      task: 'prompt_expansion',
      temperature: 0.7
    });
    const duration = Date.now() - start;
    
    console.log(`\nResponse received in ${duration}ms`);
    console.log('Raw Response Preview (First 200 chars):');
    console.log(response.response.substring(0, 200) + '...');
    
    if (response.response.length > 50) {
        console.log('✅ Prompt Expansion seems to have returned valid text.');
    } else {
        console.warn('⚠️ Response too short.');
    }

  } catch (e) {
    console.error('❌ Prompt Expansion Failed:', e);
  }

  // 4. Test Learning Analysis (Thinking Model + JSON)
  console.log('\n--- Testing Learning Analysis (Thinking Model + JSON) ---');
  try {
    const dimension = "Vocabulary";
    const recordsSummary = "User learned 'apple', 'banana' (Fruits). User struggled with 'phenomenon'.";
    
    console.log(`Dimension: ${dimension}`);
    const prompt = await serviceManager.prompt.render('analysis/learning_report', {
      dimension,
      recordsSummary
    });

    console.log('Invoking LLM (Task: analysis)...');
    const start = Date.now();
    const response = await serviceManager.llm.invoke({
      prompt,
      task: 'analysis',
      temperature: 0.3,
      jsonMode: true
    });
    const duration = Date.now() - start;

    console.log(`\nResponse received in ${duration}ms`);
    console.log('Raw Response:');
    console.log(response.response);

    // Validate JSON
    try {
        const json = JSON.parse(response.response);
        if (json.visualization && json.visualization.type) {
            console.log('✅ JSON Structure Validated (contains visualization).');
            console.log('Chart Type:', json.visualization.type);
        } else {
            console.error('❌ JSON missing visualization fields.');
        }
    } catch (jsonErr) {
        console.error('❌ Failed to parse JSON response.');
    }

  } catch (e) {
    console.error('❌ Learning Analysis Failed:', e);
  }

  // Cleanup
  await serviceManager.llm.shutdown();
}

testRealInteraction().catch(console.error);
