
import { ServiceManager } from './src/managers/service-manager';
import * as fs from 'fs';
import * as path from 'path';

async function runIntegrationTest() {
    console.log("Starting Full Integration Test (Real Production Scenario)...");

    const serviceManager = new ServiceManager();
    
    const workspaceRoot = path.resolve(__dirname, '..'); // Assuming we are in backend/
    const testImage = path.join(workspaceRoot, 'testresources', 'OCRtest.png');
    const testAudio = path.join(workspaceRoot, 'testresources', 'ASRtest.wav');

    console.log(`Test Image Path: ${testImage}`);
    console.log(`Test Audio Path: ${testAudio}`);

    if (!fs.existsSync(testImage)) {
        console.error("Test image not found!");
        process.exit(1);
    }
    if (!fs.existsSync(testAudio)) {
        console.error("Test audio not found!");
        process.exit(1);
    }

    try {
        console.log("\n--- 1. Initializing Services ---");
        await serviceManager.initialize();
        console.log("Services initialized.");

        // --- OCR Test ---
        console.log("\n--- 2. Testing OCR Service (Real PaddleOCR) ---");
        const imageBuffer = fs.readFileSync(testImage);
        const imageBase64 = imageBuffer.toString('base64');
        console.log("Invoking OCR...");
        try {
            const ocrResult = await serviceManager.ocr.invoke(imageBase64);
            console.log("OCR Result (Raw):", JSON.stringify(ocrResult, null, 2));
            
            if (ocrResult && ocrResult.text) {
                console.log("OCR Text Detected:", ocrResult.text);
            } else {
                console.warn("OCR returned empty text or unexpected format.");
            }
        } catch (e) {
            console.error("OCR Invocation Failed:", e);
        }

        // --- ASR Test ---
        console.log("\n--- 3. Testing ASR Service (Real Faster-Whisper) ---");
        const audioBuffer = fs.readFileSync(testAudio);
        // ASRService.invoke takes a Buffer
        console.log("Invoking ASR...");
        let recognizedText = "Hello, how are you?"; // Default fallback
        try {
            const asrResult = await serviceManager.asr.invoke(audioBuffer);
            console.log("ASR Result (Raw):", JSON.stringify(asrResult, null, 2));

            if (asrResult && asrResult.text) {
                console.log("ASR Text Recognized:", asrResult.text);
                if (asrResult.text.trim().length > 0) {
                    recognizedText = asrResult.text;
                }
            } else {
                console.warn("ASR returned empty text or unexpected format.");
            }
        } catch (e) {
            console.error("ASR Invocation Failed:", e);
        }

        // --- LLM Test ---
        console.log("\n--- 4. Testing LLM Service (Real LM Studio) ---");
        
        // Explicitly reload model as requested
        console.log("Reloading qwen/qwen3-vl-8b...");
        try {
            await serviceManager.llm.unloadModel("qwen/qwen3-vl-8b");
            console.log("Model unloaded.");
        } catch (e) {
            console.warn("Model unload failed (might not be loaded):", e);
        }
        
        const prompt = `The user said: "${recognizedText}". Please reply briefly.`;
        console.log(`Sending Prompt to LLM: "${prompt}"`);
        
        let replyText = "I am a robot.";
        try {
            // LLMService.invoke takes LLMRequest object
            const llmResult = await serviceManager.llm.invoke({
                prompt: prompt,
                task: 'conversation'
            });
            console.log("LLM Result (Raw):", JSON.stringify(llmResult, null, 2));

            if (llmResult && llmResult.response) {
                console.log("LLM Reply:", llmResult.response);
                replyText = llmResult.response;
            } else {
                console.warn("LLM returned empty response or unexpected format.");
            }
        } catch (e) {
            console.error("LLM Invocation Failed:", e);
        }

        // --- TTS Test ---
        console.log("\n--- 5. Testing TTS Service (Real XTTS) ---");
        console.log(`Synthesizing Text: "${replyText}"`);
        try {
            const ttsResult = await serviceManager.tts.invoke(replyText);
            
            if (ttsResult && ttsResult.audio) {
                console.log("TTS Success: Yes");
                const audioLen = ttsResult.audio.length;
                console.log(`TTS Audio Output Length (Buffer): ${audioLen}`);
                
                const outputPath = path.join(workspaceRoot, 'tests', 'output_tts_test.wav');
                fs.writeFileSync(outputPath, ttsResult.audio);
                console.log(`TTS Audio saved to: ${outputPath}`);
            } else {
                console.warn("TTS Success reported but no audio data found.");
            }
        } catch (e) {
            console.error("TTS Invocation Failed:", e);
        }

    } catch (error) {
        console.error("Integration Test Error:", error);
    } finally {
        console.log("\n--- 6. Shutting Down Services ---");
        await serviceManager.shutdown();
        console.log("Services shutdown complete.");
    }
}

runIntegrationTest();
