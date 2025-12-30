
import { LLMService } from './src/services/llm.service';
import { config } from './src/config/env';

async function runRealTest() {
    console.log('Starting REAL LLM Interaction Test...');
    console.log('WARNING: This will interact with your local LM Studio instance.');
    console.log('Ensure LM Studio is running and "lms" command is in your PATH.');
    
    const service = new LLMService();
    
    // Initialize service (starts probe)
    await service.initialize();

    // Test 1: Analysis Task (Thinking Model)
    console.log('\n--- Test 1: Analysis Task (Thinking Model) ---');
    console.log('Goal: Verify model loads with 12k context and returns valid content.');
    console.log(`Target Model: ${config.services.llm.models.analysis}`);
    
    try {
        const start = Date.now();
        const result = await service.invoke({
            prompt: 'Explain the concept of "Chain of Thought" reasoning in 3 sentences.',
            task: 'analysis'
        });
        const duration = (Date.now() - start) / 1000;
        
        console.log(`\n✅ Response Received (${duration.toFixed(1)}s):`);
        console.log('---------------------------------------------------');
        console.log(result.response);
        console.log('---------------------------------------------------');
        
        if (!result.response || result.response.length < 10) {
            console.error('❌ Content seems too short or empty!');
        } else {
            console.log('✅ Content check passed.');
        }
        
    } catch (e: any) {
        console.error('❌ Test 1 Failed:', e.message);
        if (e.response) {
            console.error('Response Data:', e.response.data);
        }
    }

    // Test 2: Conversation Task (VL Model)
    console.log('\n--- Test 2: Conversation Task (VL Model) ---');
    console.log('Goal: Verify model switches to VL model with 8k context.');
    console.log(`Target Model: ${config.services.llm.models.conversation}`);
    
    try {
        const start = Date.now();
        const result = await service.invoke({
            prompt: 'Hello! Who are you?',
            task: 'conversation'
        });
        const duration = (Date.now() - start) / 1000;
        
        console.log(`\n✅ Response Received (${duration.toFixed(1)}s):`);
        console.log('---------------------------------------------------');
        console.log(result.response);
        console.log('---------------------------------------------------');
        
        if (!result.response || result.response.length < 10) {
            console.error('❌ Content seems too short or empty!');
        } else {
            console.log('✅ Content check passed.');
        }
        
    } catch (e: any) {
        console.error('❌ Test 2 Failed:', e.message);
    }
    
    console.log('\nTest Complete. You can now inspect the output above.');
    process.exit(0);
}

runRealTest().catch(console.error);
