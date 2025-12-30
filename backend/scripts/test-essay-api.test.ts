
import { createEssayRoutes } from '../src/api/routes/essay';
import { ServiceManager } from '../src/managers/service-manager';
import { Database } from '../src/database/db';
import { LearningRecordModel } from '../src/models/learning-record';
import { EssayModel } from '../src/models/essay';
import express from 'express';
import request from 'supertest';

// Mock dependencies
jest.mock('../src/managers/service-manager');
jest.mock('../src/database/db');
jest.mock('../src/models/learning-record');
jest.mock('../src/models/essay');

// Mock Auth Middleware
jest.mock('../src/middleware/auth', () => ({
  authMiddleware: (req: any, res: any, next: any) => {
    req.userId = 'test-user-id';
    next();
  }
}));

describe('Essay API', () => {
  let app: express.Express;
  let mockServiceManager: any;
  let mockDb: any;

  beforeEach(() => {
    // Setup Model Mocks
    (LearningRecordModel as any).mockImplementation(() => ({
      create: jest.fn().mockResolvedValue({ id: 1 })
    }));

    (EssayModel as any).mockImplementation(() => ({
      create: jest.fn().mockResolvedValue({ id: 1 })
    }));

    mockDb = new Database();
    mockServiceManager = new ServiceManager();
    
    // Mock LLM Service
    mockServiceManager.llm = {
      invoke: jest.fn().mockResolvedValue({
        response: JSON.stringify({
          scores: {
            vocabulary: 8,
            grammar: 7,
            fluency: 8,
            structure: 9,
            other: 8,
            total: 8
          },
          feedback: "Good essay overall.",
          correction: "Here is the corrected version..."
        }),
        tokenUsage: { total_tokens: 100 }
      })
    };

    app = express();
    app.use(express.json());
    app.use('/api/essay', createEssayRoutes(mockDb, mockServiceManager));
  });

  it('should return essay correction and scores', async () => {
    const res = await request(app)
      .post('/api/essay/correct')
      .send({ text: 'This is a test essay.', language: 'english' });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.scores).toBeDefined();
    expect(res.body.data.scores.vocabulary).toBe(8);
    expect(res.body.data.correction).toBeDefined();
  });
});
