import { Router } from 'express';
import { authMiddleware } from '../../middleware/auth';
import { ServiceManager } from '../../managers/service-manager';
import { VoiceController } from '../../controllers/voice.controller';

export function createVoiceRoutes(serviceManager: ServiceManager): Router {
  const router = Router();
  const voiceController = new VoiceController(serviceManager);

  // Generate system prompt from user scenario
  router.post(
    '/generate-prompt',
    authMiddleware,
    voiceController.generatePrompt
  );

  // Start voice session (generate opening line)
  router.post(
    '/start',
    authMiddleware,
    voiceController.startSession
  );

  return router;
}
