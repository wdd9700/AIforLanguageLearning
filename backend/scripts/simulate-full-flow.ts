
import { ServiceManager } from '../src/managers/service-manager';
import { Database } from '../src/database/db';
import { createLearningRoutes } from '../src/api/routes/learning';
import { createQueryRoutes } from '../src/api/routes/query';
import { createEssayRoutes } from '../src/api/routes/essay';
import express from 'express';
import request from 'supertest';
import fs from 'fs';
import path from 'path';

// --- Mock Data Generators ---

const generateMockEssay = () => `
My name is Li Hua. I am a student in Beijing. I like play basketball very much. 
Yesterday I go to the park with my friend. We have a good time. 
The weather is very good, the sun is shining. 
I want to be a basketball player in the future.
`;

const generateMockAudioBuffer = () => Buffer.from('UklGRigAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=', 'base64'); // Minimal WAV header

// --- Mock Service Implementation ---
// We extend the real ServiceManager but override the 'invoke' methods to return realistic data
// without actually calling Python/GPU processes.

// Simple mock function implementation since we are not in Jest environment
const createMockFn = (impl?: Function) => {
  const fn = async (...args: any[]) => {
    if (impl) return impl(...args);
    return undefined;
  };
  (fn as any).mockImplementation = (newImpl: Function) => createMockFn(newImpl);
  (fn as any).mockResolvedValue = (val: any) => createMockFn(async () => val);
  return fn;
};

class MockServiceManager extends ServiceManager {
  constructor() {
    super();
    // Override LLM
    this.llm.invoke = createMockFn(async (params: any) => {
      const task = params.task || 'default';
      console.log(`[MockLLM] Invoked for task: ${task}`);
      
      if (task === 'learning_analysis') {
        return {
          response: JSON.stringify({
            score: 78,
            trend: 1,
            insights: [
              { type: 'strength', content: 'Vocabulary usage is consistent.' },
              { type: 'weakness', content: 'Grammar accuracy needs improvement.' }
            ],
            recommendations: ["Review past tense verbs.", "Practice complex sentence structures."],
            visualization: {
              type: "radar",
              labels: ["Vocabulary", "Grammar", "Fluency", "Coherence", "Content"],
              data: [80, 65, 75, 70, 85],
              title: "Skill Assessment"
            }
          }),
          tokenUsage: { total_tokens: 150 }
        };
      }
      
      if (task === 'vocabulary') {
        return {
          response: JSON.stringify({
            word: "serendipity",
            pronunciation: "/ˌser.ənˈdɪp.ə.ti/",
            pos: "noun",
            meaning: "The occurrence and development of events by chance in a happy or beneficial way.",
            difficulty: "Advanced",
            examples: ["It was pure serendipity that we met at the coffee shop."],
            synonyms: ["chance", "fate", "luck"]
          }),
          tokenUsage: { total_tokens: 80 }
        };
      }

      if (task === 'essay_correction') {
        return {
          response: JSON.stringify({
            scores: {
              vocabulary: 7,
              grammar: 6,
              fluency: 7,
              structure: 8,
              other: 7,
              total: 7
            },
            feedback: "The essay is understandable but contains several grammatical errors, specifically with verb tenses.",
            correction: "My name is Li Hua. I am a student in Beijing. I like **playing** basketball very much. Yesterday I **went** to the park with my friend. We **had** a good time. The weather **was** very good, **and** the sun **was** shining. I want to be a basketball player in the future."
          }),
          tokenUsage: { total_tokens: 300 }
        };
      }

      return { response: "Mock LLM Response", tokenUsage: { total_tokens: 10 } };
    }) as any;

    // Override ASR
    this.asr.invoke = createMockFn(async (audioBuffer: Buffer) => {
      console.log(`[MockASR] Processing audio buffer of size: ${audioBuffer.length}`);
      return {
        text: "Hello, I would like to learn about artificial intelligence.",
        confidence: 0.98
      };
    }) as any;

    // Override OCR
    this.ocr.invoke = createMockFn(async (image: string) => {
      console.log(`[MockOCR] Processing image...`);
      return {
        text: "This is text extracted from an image.",
        confidence: 0.95
      };
    }) as any;
  }
}

// --- Simulation Runner ---

async function runSimulation() {
  console.log("🚀 Starting Full-Flow Simulation...");
  
  // 1. Setup Environment
  const db = new Database();
  // await db.initialize(); // Assuming DB is mocked or in-memory for tests, or we use the real one if available.
  // For this script, we'll rely on the mocks in the test file context, but here we are running standalone.
  // We need to mock the DB if we don't want to write to the real file.
  // Let's use a real DB instance but maybe a temp file? 
  // Actually, let's just mock the DB methods to avoid side effects.
  
  const mockDb = {
    run: createMockFn(async () => ({})),
    get: createMockFn(async () => ({})),
    all: createMockFn(async () => ([])),
    exec: createMockFn(async () => ({})),
    insert: createMockFn(async () => 123) // Mock insert method
  } as any;

  const serviceManager = new MockServiceManager();
  const app = express();
  app.use(express.json());
  
  // Mount Routes
  app.use('/api/learning', createLearningRoutes(mockDb, serviceManager));
  app.use('/api/query', createQueryRoutes(mockDb, serviceManager));
  app.use('/api/essay', createEssayRoutes(mockDb, serviceManager));

  // Mock Auth Middleware (Global)
  // Note: The routes use the real authMiddleware which checks headers.
  // We need to override it at the router level OR mock the import.
  // Since we are importing createLearningRoutes which imports authMiddleware, 
  // we can't easily mock the import in this script without a bundler/test runner.
  // Instead, we will generate a valid token for the simulation.
  
  const jwt = require('jsonwebtoken');
  // Use the secret from the config file we just read
  const secret = 'your-super-secret-key-change-this-in-production';
  process.env.JWT_SECRET = secret;
  
  const token = jwt.sign({ userId: 1, username: 'sim-user' }, secret); 

  // --- Scenario 1: Vocabulary Query ---
  console.log("\n--- Scenario 1: Vocabulary Query ---");
  const vocabRes = await request(app)
    .post('/api/query/vocabulary')
    .set('Authorization', `Bearer ${token}`)
    .send({ word: 'serendipity' });
  
  console.log("Status:", vocabRes.status);
  console.log("Response Data:", JSON.stringify(vocabRes.body.data, null, 2));
  
  if (vocabRes.body.data.word === 'serendipity' && vocabRes.body.data.meaning) {
    console.log("✅ Vocabulary Query Passed");
  } else {
    console.error("❌ Vocabulary Query Failed");
  }

  // --- Scenario 2: Essay Correction ---
  console.log("\n--- Scenario 2: Essay Correction ---");
  const essayText = generateMockEssay();
  const essayRes = await request(app)
    .post('/api/essay/correct')
    .set('Authorization', `Bearer ${token}`)
    .send({ text: essayText });

  console.log("Status:", essayRes.status);
  console.log("Scores:", essayRes.body.data.scores);
  console.log("Feedback:", essayRes.body.data.feedback);
  console.log("Correction Preview:", essayRes.body.data.correction.substring(0, 100) + "...");

  if (essayRes.body.data.scores.total > 0 && essayRes.body.data.correction) {
    console.log("✅ Essay Correction Passed");
  } else {
    console.error("❌ Essay Correction Failed");
  }

  // --- Scenario 3: Learning Analysis ---
  console.log("\n--- Scenario 3: Learning Analysis ---");
  // Mock DB return for analysis
  mockDb.all = createMockFn(async () => ([
    { type: 'vocabulary', content: 'apple', created_at: new Date() },
    { type: 'essay', content: 'My essay...', created_at: new Date() }
  ]));

  const analysisRes = await request(app)
    .post('/api/learning/analyze')
    .set('Authorization', `Bearer ${token}`)
    .send({ dimension: 'overall' });

  console.log("Status:", analysisRes.status);
  console.log("Visualization Type:", analysisRes.body.data.visualization.type);
  console.log("Insights:", analysisRes.body.data.insights);

  if (analysisRes.body.data.visualization && analysisRes.body.data.insights.length > 0) {
    console.log("✅ Learning Analysis Passed");
  } else {
    console.error("❌ Learning Analysis Failed");
  }

  // --- Scenario 4: Voice Input Simulation (ASR -> LLM) ---
  console.log("\n--- Scenario 4: Voice Input Simulation ---");
  // Let's test the /api/query/voice endpoint which does ASR -> LLM
  const audioBase64 = generateMockAudioBuffer().toString('base64');
  const voiceRes = await request(app)
    .post('/api/query/voice')
    .set('Authorization', `Bearer ${token}`)
    .send({ audio: audioBase64 });

  console.log("Status:", voiceRes.status);
  console.log("Detected Text:", voiceRes.body.data.detectedText);
  console.log("Explanation:", voiceRes.body.data.explanation);

  if (voiceRes.body.data.detectedText && voiceRes.body.data.explanation) {
    console.log("✅ Voice Input Passed");
  } else {
    console.error("❌ Voice Input Failed");
  }

  console.log("\n🚀 Simulation Complete.");
}

// Run the simulation
runSimulation().catch(console.error);
