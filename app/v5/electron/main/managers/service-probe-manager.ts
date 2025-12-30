import Store from 'electron-store';
import log from 'electron-log';
import { WindowManager } from './window-manager.js';
import { Config, SKey, SState, Ports } from '../types.js';

export class ServiceProbeManager {
    private serviceState: Record<SKey, SState> = {
        lmstudio: { status: 'stopped' },
        whisper: { status: 'stopped' },
        surya: { status: 'stopped' },
        cosy: { status: 'stopped' }
    };
    private probeTimer: NodeJS.Timeout | null = null;
    private store: Store<Config>;
    private windowManager: WindowManager;

    constructor(store: Store<Config>, windowManager: WindowManager) {
        this.store = store;
        this.windowManager = windowManager;
    }

    public async probeOnce(): Promise<void> {
        const cfgPorts = (this.store.get('ports') as Ports) || {};
        const entries: [SKey, number | null, string[]][] = [
            ['lmstudio', cfgPorts?.lmstudio ?? null, ['/v1/models', '/status']],
            ['whisper', cfgPorts?.whisper ?? null, ['/health', '/']],
            ['surya', cfgPorts?.surya ?? null, ['/health', '/']],
            ['cosy', cfgPorts?.cosy ?? null, ['/health', '/']]
        ];
        const now = Date.now();

        await Promise.all(entries.map(async ([key, port, paths]) => {
            if (!port) return;
            for (const pth of paths) {
                try {
                    const resp = await fetch(`http://127.0.0.1:${port}${pth}`, { method: 'GET' });
                    if (resp.ok) {
                        this.serviceState[key] = { status: 'running', lastProbe: now };
                        this.windowManager.send('service:update', { key, state: this.serviceState[key] });
                        return;
                    }
                } catch { /* next */ }
            }
            if (this.serviceState[key].status !== 'starting') {
                this.serviceState[key] = { status: 'error', message: 'No response', lastProbe: now };
            } else {
                this.serviceState[key].lastProbe = now;
            }
            this.windowManager.send('service:update', { key, state: this.serviceState[key] });
        }));
    }

    public startProbing() {
        if (this.probeTimer) clearInterval(this.probeTimer);
        this.probeTimer = setInterval(() => {
            this.probeOnce().catch(e => log.warn('probe error', e));
        }, 5000);
    }

    public stopProbing() {
        if (this.probeTimer) clearInterval(this.probeTimer);
    }

    public async initializeServicesVisual() {
        for (const key of ['lmstudio', 'whisper', 'surya', 'cosy'] as SKey[]) {
            this.serviceState[key] = { status: 'starting', message: 'Initializing...' };
            this.windowManager.send('service:update', { key, state: this.serviceState[key] });
        }
        await this.probeOnce();
    }

    public reloadServices() {
        log.info('Reload services requested');
        this.initializeServicesVisual();
    }

    public updateState(key: SKey, state: SState) {
        this.serviceState[key] = state;
        this.windowManager.send('service:update', { key, state });
    }

    public getState() {
        return this.serviceState;
    }
}
