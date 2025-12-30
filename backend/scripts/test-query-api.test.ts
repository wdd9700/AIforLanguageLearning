
import { createQueryRoutes } from '../src/api/routes/query';
import { ServiceManager } from '../src/managers/service-manager';
import { Database } from '../src/database/db';
import { LearningRecordModel } from '../src/models/learning-record';
import { VocabularyModel } from '../src/models/vocabulary';
import express from 'express';
import request from 'supertest';

// Mock dependencies
jest.mock('../src/managers/service-manager');
jest.mock('../src/database/db');
jest.mock('../src/models/learning-record');
jest.mock('../src/models/vocabulary');

// Mock Auth Middleware
jest.mock('../src/middleware/auth', () => ({
  authMiddleware: (req: any, res: any, next: any) => {
    req.userId = 'test-user-id';
    next();
  }
}));

describe('Query API', () => {
  let app: express.Express;
  let mockServiceManager: any;
  let mockDb: any;

  beforeEach(() => {
    // Setup Model Mocks
    (LearningRecordModel as any).mockImplementation(() => ({
      create: jest.fn().mockResolvedValue({ id: 1 })
    }));

    (VocabularyModel as any).mockImplementation(() => ({
      addWord: jest.fn().mockResolvedValue({ id: 1 })
    }));

    mockDb = new Database();
    mockServiceManager = new ServiceManager();
    
    // Mock LLM Service
    mockServiceManager.llm = {
      invoke: jest.fn().mockResolvedValue({
        response: JSON.stringify({
          word: "apple",
          pronunciation: "/ˈæp.l/",
          pos: "noun",
          meaning: "A round fruit with red or green skin and a white inside.",
          difficulty: "Beginner",
          examples: ["I ate an apple for lunch."],
          synonyms: ["fruit"]
        }),
        tokenUsage: { total_tokens: 50 }
      })
    };

    app = express();
    app.use(express.json());
    app.use('/api/query', createQueryRoutes(mockDb, mockServiceManager));
  });

  it('should return vocabulary definition', async () => {
    const res = await request(app)
      .post('/api/query/vocabulary')
      .send({ word: 'apple' });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.word).toBe('apple');
    expect(res.body.data.meaning).toBeDefined();
    expect(res.body.data.examples).toHaveLength(1);
  });
});
