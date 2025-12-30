import { app, BrowserWindow } from 'electron';
import path from 'node:path';
import fs from 'node:fs';
import log from 'electron-log';
import Store from 'electron-store';
import { initializeSoftbus, cleanupSoftbus } from './softbus-integration.js';
import { initializeOrchestrator } from './orchestrator-integration.js';
import { WindowManager } from './managers/window-manager.js';
import { ServiceProbeManager } from './managers/service-probe-manager.js';
import { IpcManager } from './managers/ipc-manager.js';
import { SystemIntegrationManager } from './managers/system-integration-manager.js';
import { Config } from './types.js';

// Log setup
log.initialize({ preload: true });
log.transports.file.level = 'info';
log.transports.file.resolvePathFn = (_variables) => {
    const logDir = path.join(app.getPath('userData'), 'logs');
    if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
    return path.join(logDir, 'app.log');
};
log.info('App starting...');

// Store setup
const store = new Store<Config>({
    name: 'config',
    defaults: {
        ports: { lmstudio: null, whisper: null, surya: null, cosy: null, app: 0 },
        theme: 'system',
        backendUrl: 'localhost:8011',
        backend: {
            url: 'http://localhost:8011',
            wsUrl: 'localhost:8011'
        },
        general: { theme: 'system', language: 'zh-CN', autoUpdate: true },
        audio: { inputDevice: 'default', outputDevice: 'default', volume: 80 },
        ai: { model: 'gpt-4-turbo', temperature: 0.7, voice: 'alloy' }
    }
});

// Managers
const windowManager = new WindowManager();
const serviceProbeManager = new ServiceProbeManager(store, windowManager);
const ipcManager = new IpcManager(store, windowManager, serviceProbeManager);
const systemIntegrationManager = new SystemIntegrationManager(windowManager, serviceProbeManager);

// Register IPC handlers
ipcManager.registerHandlers();

app.on('ready', () => {
    const mainWindow = windowManager.createMainWindow();
    systemIntegrationManager.createTray();
    systemIntegrationManager.registerShortcuts();
    serviceProbeManager.initializeServicesVisual();
    serviceProbeManager.startProbing();

    // Initialize Softbus
    if (mainWindow) {
        const softbusEndpoint = 'tcp://127.0.0.1:5555';
        initializeSoftbus(softbusEndpoint, mainWindow).then(async (client) => {
            const config = {
                services: {
                    llm: {
                        name: 'llm',
                        type: 'http' as const,
                        endpoint: 'http://localhost:1234/v1',
                        model: 'qwen2.5-7b-instruct'
                    },
                    tts: {
                        name: 'tts',
                        type: 'http' as const,
                        endpoint: 'http://localhost:8011'
                    },
                    asr: {
                        name: 'asr',
                        type: 'http' as const,
                        endpoint: 'http://localhost:9000'
                    }
                },
                routes: [],
                pipelines: {
                    'voice-dialogue-start': {
                        name: 'voice-dialogue-start',
                        steps: [
                            { name: 'start-asr', serviceName: 'asr', action: 'start-stream' },
                            { name: 'connect-llm', serviceName: 'llm', action: 'connect' }
                        ]
                    }
                }
            };

            const storedPorts = store.get('ports');
            const storedLlmEndpoint = store.get('llmEndpoint');

            if (config.services.llm) {
                if (storedLlmEndpoint) {
                    let baseUrl = (storedLlmEndpoint as string).replace(/\/v1\/chat\/completions\/?$/, '');
                    if (baseUrl.endsWith('/')) baseUrl = baseUrl.slice(0, -1);
                    config.services.llm.endpoint = baseUrl;
                } else if (storedPorts && storedPorts.lmstudio) {
                    config.services.llm.endpoint = `http://localhost:${storedPorts.lmstudio}`;
                }
            }

            // @ts-ignore
            await initializeOrchestrator(config, mainWindow, client);
        }).catch(err => {
            log.warn('Softbus/Orchestrator initialization failed (non-fatal):', err);
        });
    }

    // Permission handler
    if (mainWindow) {
        mainWindow.webContents.session.setPermissionRequestHandler((webContents, permission, callback) => {
            if (permission === 'media') {
                callback(true);
            } else {
                callback(false);
            }
        });
    }
});

app.on('window-all-closed', () => { /* Keep running */ });

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) windowManager.createMainWindow();
});

app.on('before-quit', async () => {
    windowManager.setQuitting(true);
    serviceProbeManager.stopProbing();
    systemIntegrationManager.unregisterShortcuts();
    await cleanupSoftbus();
    log.info('App quitting');
});
