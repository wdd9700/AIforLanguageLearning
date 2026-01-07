# AI for Foreign Language Learning

An all-in-one local AI assistant for foreign language learning, integrating vocabulary analysis, essay correction, and voice dialogue features.

## Project Structure

- **app/v5**: Frontend application built with Vue 3, Vite, and Pinia.
- **backend_fastapi**: Modern backend service using FastAPI, supporting LLM integration (OpenAI-compatible / LM Studio).
- **backend**: Legacy backend service (Node.js/Typescript).
- **scripts**: PowerShell and Python scripts for environment setup, health checks, and service management.

## Features

- **Vocabulary Query**: Deep analysis of words with definitions, examples, and translations.
- **Essay Correction**: Grammar checking, scoring, and rewriting suggestions provided by LLM.
- **Voice Interaction**: Real-time spoken dialogue practice (ASR/TTS integration).

## Getting Started

### Prerequisites

- Windows OS (Testing environment)
- Python 3.10+
- Node.js & npm
- LM Studio (or compatible LLM server) running locally

### Running the Application

Use the provided PowerShell script to start services:

```powershell
./scripts/start.ps1
```

This script will:
1. Check for necessary dependencies.
2. Start the FastAPI backend (Default port: 8012).
3. Start the Frontend application.

## Configuration

- Backend settings can be configured in `.env` or `backend_fastapi/app/settings.py`.
- Frontend API endpoints are configured in `app/v5/src/services/config.ts`.
