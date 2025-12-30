
import { createLearningRoutes } from '../src/api/routes/learning';
import { ServiceManager } from '../src/managers/service-manager';
import { Database } from '../src/database/db';
import { LearningRecordModel } from '../src/models/learning-record';
import express from 'express';
import request from 'supertest';

// Mock dependencies
jest.mock('../src/managers/service-manager');
jest.mock('../src/database/db');
jest.mock('../src/models/learning-record');
jest.mock('../src/models/student');
jest.mock('../src/models/vocabulary');
jest.mock('../src/models/essay');

// Fix: Move auth mock to a separate variable or use a simpler mock
jest.mock('../src/middleware/auth', () => ({
  authMiddleware: (req: any, res: any, next: any) => {
    req.userId = 'test-user-id';
    next();
  }
}));

describe('Learning Analysis API', () => {
  let app: express.Express;
  let mockServiceManager: any;
  let mockDb: any;

  beforeEach(() => {
    // Setup Model Mocks
    (LearningRecordModel as any).mockImplementation(() => ({
      getByUser: jest.fn().mockResolvedValue([
        { type: 'vocabulary', content: 'word1', created_at: new Date() },
        { type: 'essay', content: 'essay content', created_at: new Date() }
      ]),
      create: jest.fn().mockResolvedValue({ id: 1 }),
      countByUserAndType: jest.fn().mockResolvedValue(5),
      getByUserAndType: jest.fn().mockResolvedValue([])
    }));

    mockDb = new Database();
    mockServiceManager = new ServiceManager();
    
    // Mock LLM Service
    mockServiceManager.llm = {
      invoke: jest.fn().mockResolvedValue({
        response: JSON.stringify({
          score: 85,
          trend: 1,
          insights: ["Good progress"],
          recommendations: ["Keep going"],
          visualization: {
            type: "radar",
            labels: ["Vocab", "Grammar"],
            data: [80, 90],
            title: "Skill Radar"
          }
        }),
        tokenUsage: { total_tokens: 100 }
      })
    };

    app = express();
    app.use(express.json());
    app.use('/api/learning', createLearningRoutes(mockDb, mockServiceManager));
  });

  it('should return visualization data in analysis result', async () => {
    const res = await request(app)
      .post('/api/learning/analyze')
      .send({ dimension: 'vocabulary' });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.visualization).toBeDefined();
    expect(res.body.data.visualization.type).toBe('radar');
    expect(res.body.data.visualization.data).toEqual([80, 90]);
  });
});
