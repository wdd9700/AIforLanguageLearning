import { Tray, Menu, nativeImage, globalShortcut, clipboard, app } from 'electron';
import log from 'electron-log';
import fs from 'node:fs';
import { WindowManager } from './window-manager.js';
import { ServiceProbeManager } from './service-probe-manager.js';
import { getRendererFile } from '../utils.js';

export class SystemIntegrationManager {
    private tray: Tray | null = null;
    private windowManager: WindowManager;
    private serviceProbeManager: ServiceProbeManager;

    constructor(windowManager: WindowManager, serviceProbeManager: ServiceProbeManager) {
        this.windowManager = windowManager;
        this.serviceProbeManager = serviceProbeManager;
    }

    public createTray() {
        const iconPath = getRendererFile('icon.png');
        const img = fs.existsSync(iconPath) ? nativeImage.createFromPath(iconPath) : nativeImage.createEmpty();
        this.tray = new Tray(img);
        const contextMenu = Menu.buildFromTemplate([
            { label: 'Show Window', click: () => this.windowManager.show() },
            { type: 'separator' },
            { label: 'Reload Services', click: () => this.serviceProbeManager.reloadServices() },
            { type: 'separator' },
            { label: 'Quit', click: () => { 
                this.windowManager.setQuitting(true);
                app.quit(); 
            } }
        ]);
        this.tray.setToolTip('MMLS Services');
        this.tray.setContextMenu(contextMenu);
        this.tray.on('click', () => this.windowManager.show());
    }

    public registerShortcuts() {
        try {
            const ok = globalShortcut.register('CommandOrControl+Shift+L', () => {
                log.info('Global hotkey triggered: vocabulary lookup');
                
                const text = clipboard.readText();
                if (text && text.trim()) {
                    this.windowManager.show();
                    this.windowManager.send('trigger-lookup', { type: 'text', content: text.trim() });
                    return;
                }
                
                const image = clipboard.readImage();
                if (!image.isEmpty()) {
                    this.windowManager.show();
                    const base64 = image.toPNG().toString('base64');
                    this.windowManager.send('trigger-lookup', { type: 'image', content: base64 });
                    return;
                }
                
                this.windowManager.show();
            });
            if (!ok) log.warn('Hotkey not registered');
        } catch (e) {
            log.error('registerShortcuts error', e);
        }
    }

    public unregisterShortcuts() {
        globalShortcut.unregisterAll();
    }
}
