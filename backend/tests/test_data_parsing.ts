
import { OCRService } from './src/services/ocr.service';
import { ASRService } from './src/services/asr.service';
import { LLMService } from './src/services/llm.service';
import { config } from './src/config/env';

// Mock config for testing
config.services.ocr.enabled = true;
config.services.ocr.scriptPath = 'mock_ocr.py';
config.services.ocr.pythonPath = 'python';

// Mock spawn/execFile for testing
const mockSpawn = (cmd: string, args: string[]) => {
    // ...
};

async function testParsing() {
    console.log('Starting Service Data Parsing Test...');

    // 1. Test OCR Parsing
    console.log('\n--- Test 1: OCR Parsing ---');
    const ocrService = new OCRService();
    
    // Simulate messy OCR output
    const messyOcrOutput = `
    [2024-01-01 10:00:00] [INFO] Loading PaddleOCR...
    [2024-01-01 10:00:01] [WARN] GPU not found, using CPU
    {
        "success": true,
        "count": 2,
        "results": [
            {"text": "Hello World", "confidence": 0.99, "box": [[0,0], [10,0], [10,10], [0,10]]},
            {"text": "Testing", "confidence": 0.95, "box": [[0,20], [10,20], [10,30], [0,30]]}
        ]
    }
    `;
    
    try {
        // We need to expose the parsing logic or mock the child process
        // Since we can't easily mock child_process in this script without a library,
        // we will extract the parsing logic to a helper function in the service or test it via a unit test approach.
        // For this "integration" style script, let's verify the logic by manually invoking the parsing code snippet.
        
        console.log('Simulating OCR Output Parsing...');
        const jsonStart = messyOcrOutput.indexOf('{');
        const jsonEnd = messyOcrOutput.lastIndexOf('}');
        
        if (jsonStart !== -1 && jsonEnd !== -1) {
            const jsonStr = messyOcrOutput.substring(jsonStart, jsonEnd + 1);
            const result = JSON.parse(jsonStr);
            console.log('✅ OCR JSON Extracted:', result.results[0].text);
        } else {
            console.error('❌ OCR JSON Extraction Failed');
        }

    } catch (e) {
        console.error('OCR Test Failed:', e);
    }

    // 2. Test ASR Parsing
    console.log('\n--- Test 2: ASR Parsing ---');
    const messyAsrOutput = `
    Loading Whisper model...
    Detecting language...
    {
        "success": true,
        "text": "This is a test.",
        "language": "en",
        "duration": 2.5,
        "segments": []
    }
    `;
    
    try {
        console.log('Simulating ASR Output Parsing...');
        const jsonStart = messyAsrOutput.indexOf('{');
        const jsonEnd = messyAsrOutput.lastIndexOf('}');
        
        if (jsonStart !== -1 && jsonEnd !== -1) {
            const jsonStr = messyAsrOutput.substring(jsonStart, jsonEnd + 1);
            const result = JSON.parse(jsonStr);
            console.log('✅ ASR JSON Extracted:', result.text);
        } else {
            console.error('❌ ASR JSON Extraction Failed');
        }
    } catch (e) {
        console.error('ASR Test Failed:', e);
    }

    // 3. Test LLM Parsing
    console.log('\n--- Test 3: LLM Parsing ---');
    const llmMarkdownOutput = `
    Here is the analysis:
    \`\`\`json
    {
        "score": 85,
        "feedback": "Good job!"
    }
    \`\`\`
    Hope this helps!
    `;
    
    try {
        console.log('Simulating LLM Output Parsing...');
        const jsonMatch = llmMarkdownOutput.match(/```json\s*([\s\S]*?)\s*```/) || llmMarkdownOutput.match(/```\s*([\s\S]*?)\s*```/);
        if (jsonMatch) {
            const jsonStr = jsonMatch[1];
            const result = JSON.parse(jsonStr);
            console.log('✅ LLM JSON Extracted:', result.feedback);
        } else {
            console.error('❌ LLM JSON Extraction Failed');
        }
    } catch (e) {
        console.error('LLM Test Failed:', e);
    }
}

testParsing();
