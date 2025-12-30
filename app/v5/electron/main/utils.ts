import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { app } from 'electron';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Assuming structure:
// src/main/utils.ts -> dist/src/main/utils.js
// Renderer is at dist/src/renderer

// From dist/src/main/utils.js, we need to go up to dist/src/renderer
// ../ -> dist/src/main
// ../../ -> dist/src
// ../../renderer -> dist/src/renderer

const distRenderer = path.join(__dirname, '..', '..', 'dist');

export function getRendererFile(rel: string): string {
    const dist = path.join(distRenderer, rel);
    return dist;
}

export function getPreloadPath(): string {
    // preload.js should be in the same folder as main.js (dist/src/main/preload.js)
    return path.join(__dirname, 'preload.js');
}
