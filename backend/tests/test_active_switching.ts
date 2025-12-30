
import { LLMService } from './src/services/llm.service';
import { config } from './src/config/env';

// Simple mock for Axios
const mockPost = async () => ({
    data: {
        choices: [{ message: { content: 'Mock Response' } }],
        usage: { total_tokens: 10 }
    }
});

// Subclass to mock CLI
class TestLLMService extends LLMService {
    public commandLog: string[] = [];
    public loadedModelsMock: any[] = [];

    protected async runLMSCommand(command: string): Promise<{ ok: boolean; stdout?: string; stderr?: string; error?: string }> {
        this.commandLog.push(command);
        
        if (command.includes('ps --json')) {
            return { ok: true, stdout: JSON.stringify(this.loadedModelsMock) };
        }
        
        if (command.includes('load')) {
             // Extract model ID from command for mock state
             // lms load <model> ...
             const parts = command.split(' ');
             // Simple extraction, might need adjustment if flags come before model
             // But our code does `lms load ${modelPath} ${extraArgs}`
             const modelId = parts[2];
             this.loadedModelsMock.push({ identifier: modelId, path: modelId });
             return { ok: true, stdout: 'Loaded' };
        }

        if (command.includes('unload')) {
            if (command.includes('--all')) {
                this.loadedModelsMock = [];
            } else {
                // Remove specific
            }
            return { ok: true, stdout: 'Unloaded' };
        }

        return { ok: true, stdout: '' };
    }

    // Helper to inject mock client
    public setMockClient() {
        (this as any).client = {
            post: mockPost,
            get: async () => ({ data: [] })
        };
        (this as any).apiReachable = true;
    }
}

async function runTest() {
    console.log('Starting Active Model Switching Test...');
    
    const service = new TestLLMService();
    service.setMockClient();

    // Test 1: Analysis Task (Thinking Model)
    console.log('\n--- Test 1: Analysis Task ---');
    // Pre-condition: No models loaded
    service.loadedModelsMock = [];
    
    try {
        await service.invoke({
            prompt: 'Analyze this',
            task: 'analysis'
        });
    } catch (e) {
        console.error('Invoke failed:', e);
    }

    // Verify commands
    const analysisModel = config.services.llm.models.analysis;
    const analysisLoadCmd = service.commandLog.find(cmd => cmd.includes(`load ${analysisModel}`));
    
    if (analysisLoadCmd) {
        console.log('✅ Analysis model loaded');
        console.log('   Command:', analysisLoadCmd);
        // Check for specific args
        if (analysisLoadCmd.includes('--gpu-offload-ratio 1') && analysisLoadCmd.includes('--context-length 4096')) {
             console.log('✅ Correct arguments used');
        } else {
             console.error('❌ Incorrect arguments:', analysisLoadCmd);
        }
    } else {
        console.error('❌ Analysis model NOT loaded');
        console.log('Log:', service.commandLog);
    }

    // Test 2: Conversation Task (VL Model)
    console.log('\n--- Test 2: Conversation Task ---');
    // Pre-condition: Analysis model is loaded (from previous step, if it worked)
    // But let's ensure our mock state reflects it
    service.loadedModelsMock = [{ identifier: analysisModel, path: analysisModel }];
    service.commandLog = []; // Reset log
    
    try {
        await service.invoke({
            prompt: 'Hello',
            task: 'conversation'
        });
    } catch (e) {
        console.error('Invoke failed:', e);
    }

    // Verify unload and load
    // The implementation iterates and unloads individually, so we look for unload of the previous model
    const previousModel = config.services.llm.models.analysis;
    const unloadCmd = service.commandLog.find(cmd => cmd.includes(`unload ${previousModel}`));
    const conversationModel = config.services.llm.models.conversation;
    const convLoadCmd = service.commandLog.find(cmd => cmd.includes(`load ${conversationModel}`));

    if (unloadCmd) {
        console.log('✅ Unload previous model called');
    } else {
        console.error('❌ Unload previous model NOT called');
        console.log('Full Command Log:', service.commandLog);
    }

    if (convLoadCmd) {
        console.log('✅ Conversation model loaded');
        console.log('   Command:', convLoadCmd);
         if (convLoadCmd.includes('--gpu-offload-ratio 1') && convLoadCmd.includes('--context-length 8192')) {
             console.log('✅ Correct arguments used');
        } else {
             console.error('❌ Incorrect arguments:', convLoadCmd);
        }
    } else {
        console.error('❌ Conversation model NOT loaded');
        console.log('Log:', service.commandLog);
    }
}

runTest().catch(console.error);
