
import { createStreamHandler } from '../src/api/handlers/stream';
import { ServiceManager } from '../src/managers/service-manager';
import { SessionManager } from '../src/managers/session-manager';
import axios from 'axios';
import { EventEmitter } from 'events';

// Mock dependencies
jest.mock('../src/managers/service-manager');
jest.mock('../src/managers/session-manager');
jest.mock('axios');

describe('Voice Dialogue WebSocket Handler', () => {
  let mockServiceManager: any;
  let mockSessionManager: any;
  let mockWs: any;
  let mockAsrProcess: any;
  let mockTtsProcess: any;
  let handler: any;

  beforeEach(() => {
    // Mock Processes
    mockAsrProcess = {
      stdin: { write: jest.fn() },
      stdout: new EventEmitter(),
      kill: jest.fn()
    };
    mockTtsProcess = {
      stdin: { write: jest.fn() },
      stdout: new EventEmitter(),
      kill: jest.fn()
    };

    // Mock Service Manager
    mockServiceManager = new ServiceManager();
    mockServiceManager.asr = {
      start: jest.fn().mockReturnValue(mockAsrProcess),
      shutdown: jest.fn()
    };
    mockServiceManager.tts = {
      start: jest.fn().mockReturnValue(mockTtsProcess),
      shutdown: jest.fn()
    };

    mockSessionManager = new SessionManager(null as any);

    // Mock WebSocket
    mockWs = new EventEmitter();
    mockWs.send = jest.fn();
    mockWs.readyState = 1; // OPEN

    // Mock Axios for LLM
    const mockStream = new EventEmitter();
    (axios.post as jest.Mock).mockResolvedValue({
      data: mockStream
    });

    handler = createStreamHandler(mockServiceManager, mockSessionManager);
    handler(mockWs, {});
  });

  it('should handle "start" message and initialize services', () => {
    mockWs.emit('message', JSON.stringify({ type: 'start' }), false);

    expect(mockServiceManager.asr.start).toHaveBeenCalled();
    expect(mockServiceManager.tts.start).toHaveBeenCalled();
    expect(mockWs.send).toHaveBeenCalledWith(expect.stringContaining('"status":"ready"'));
  });

  it('should handle "page_mounted" message', () => {
    mockWs.emit('message', JSON.stringify({ type: 'page_mounted', data: { page: 'voice-dialogue' } }), false);

    expect(mockServiceManager.asr.start).toHaveBeenCalled();
    expect(mockServiceManager.tts.start).toHaveBeenCalled();
    expect(mockWs.send).toHaveBeenCalledWith(expect.stringContaining('"services":{"asr":"running","tts":"running"}'));
  });

  it('should trigger LLM when ASR returns text', async () => {
    // 1. Start session
    mockWs.emit('message', JSON.stringify({ type: 'start' }), false);

    // 2. Simulate ASR output
    const asrOutput = JSON.stringify({ type: 'transcription', text: 'Hello AI' });
    mockAsrProcess.stdout.emit('data', asrOutput + '\n');

    // 3. Verify ASR result sent to client
    // Note: The current implementation overwrites 'type' with event.type ('transcription')
    expect(mockWs.send).toHaveBeenCalledWith(expect.stringContaining('"type":"transcription"'));
    expect(mockWs.send).toHaveBeenCalledWith(expect.stringContaining('"text":"Hello AI"'));

    // 4. Verify LLM triggered (axios called)
    // Wait for async operations
    await new Promise(resolve => setTimeout(resolve, 10));
    expect(axios.post).toHaveBeenCalled();
    expect(mockWs.send).toHaveBeenCalledWith(expect.stringContaining('"type":"llm_start"'));
  });
});
