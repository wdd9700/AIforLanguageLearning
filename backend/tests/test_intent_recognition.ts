
import { LLMService } from './src/services/llm.service';
import { config } from './src/config/env';
import * as fs from 'fs';
import * as path from 'path';

async function runTest() {
    console.log('Starting Intent Recognition Test...');
    
    const service = new LLMService();
    await service.initialize();

    const promptTemplate = fs.readFileSync(
        path.join(__dirname, 'src/prompts/router/intent_classification.md'), 
        'utf-8'
    );

    const testCases = [
        "Hello, how are you today?",
        "Can you analyze my pronunciation in the last sentence?",
        "Stop the conversation.",
        "I want to learn about business english.",
        "Please give me a report on my grammar usage."
    ];

    for (const input of testCases) {
        console.log(`\nInput: "${input}"`);
        const prompt = promptTemplate.replace('{{userInput}}', input);
        
        try {
            const result = await service.invoke({
                prompt,
                task: 'router', // Uses qwen3-vl-8b
                jsonMode: true,
                temperature: 0.1 // Low temp for classification
            });

            console.log('Raw Response:', result.response);
            
            if (result.parsedJson) {
                console.log('✅ Parsed JSON:', result.parsedJson);
            } else {
                console.log('❌ Failed to parse JSON');
            }

        } catch (e: any) {
            console.error('Error:', e.message);
        }
    }
    
    process.exit(0);
}

runTest().catch(console.error);
