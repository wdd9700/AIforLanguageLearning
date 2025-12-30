import { BrowserWindow, screen, nativeTheme, app } from 'electron';
import path from 'node:path';
import fs from 'node:fs';
import log from 'electron-log';
import { getRendererFile, getPreloadPath } from '../utils.js';

export class WindowManager {
    public mainWindow: BrowserWindow | null = null;
    public overlayWindow: BrowserWindow | null = null;
    private isQuitting = false;

    constructor() {}

    public createMainWindow(): BrowserWindow {
        this.mainWindow = new BrowserWindow({
            width: 1200,
            height: 780,
            minWidth: 1080,
            minHeight: 700,
            title: 'Multimodal Learning System',
            titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
            backgroundColor: nativeTheme.shouldUseDarkColors ? '#121212' : '#f7f7f9',
            webPreferences: {
                preload: getPreloadPath(),
                nodeIntegration: false,
                contextIsolation: true,
                sandbox: false
            }
        });

        const indexPath = getRendererFile('index.html');
        
        // V5 Migration: Support loading from Vite Dev Server
        if (process.env.VITE_DEV_SERVER_URL) {
            log.info('Loading V5 Dev Server:', process.env.VITE_DEV_SERVER_URL);
            this.mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
        } else if (!fs.existsSync(indexPath)) {
            log.error('Renderer index.html not found at', indexPath);
        } else {
            this.mainWindow.loadFile(indexPath).catch(err => log.error('loadFile error', err));
        }

        this.mainWindow.on('close', (e) => {
            if (!this.isQuitting) {
                e.preventDefault();
                this.mainWindow?.hide();
            }
        });

        this.mainWindow.on('closed', () => {
            this.mainWindow = null;
        });

        return this.mainWindow;
    }

    public showOverlay(title: string, text: string) {
        try {
            if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
                this.overlayWindow.close();
            }
            this.overlayWindow = new BrowserWindow({
                width: 420,
                height: 260,
                frame: false,
                transparent: true,
                resizable: false,
                alwaysOnTop: true,
                skipTaskbar: true,
                show: false,
                webPreferences: { contextIsolation: true }
            });

            const display = screen.getPrimaryDisplay();
            const x = display.workArea.x + display.workArea.width - 460;
            const y = display.workArea.y + 40;
            this.overlayWindow.setPosition(x, y);

            const url = new URL('file://' + getRendererFile('overlay.html'));
            url.searchParams.set('title', encodeURIComponent(title));
            url.searchParams.set('text', encodeURIComponent(text));

            this.overlayWindow.loadURL(url.toString());
            this.overlayWindow.once('ready-to-show', () => this.overlayWindow?.show());
            this.overlayWindow.on('blur', () => this.overlayWindow?.close());
        } catch (e) {
            log.error('showOverlay error', e);
        }
    }

    public send(channel: string, data: any) {
        if (this.mainWindow && !this.mainWindow.isDestroyed()) {
            this.mainWindow.webContents.send(channel, data);
        }
    }

    public show() {
        if (this.mainWindow) {
            if (this.mainWindow.isMinimized()) this.mainWindow.restore();
            this.mainWindow.show();
        }
    }

    public setQuitting(val: boolean) {
        this.isQuitting = val;
    }
}
