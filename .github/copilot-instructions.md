# Copilot Instructions

## Project Structure
Before making changes, understand the codebase structure:
- Run `outln src` or `outln server` to see file purposes
- Each file has a header comment describing its responsibility

## Conventions
- One responsibility per file
- Every file must have a JSDoc header comment at the top
- File name should describe its purpose

## Key Components
- `server/` — Express backend, WebSocket, RFID services
- `client/` — React frontend
- `shared/` — Shared types and schemas
- `bookcabinet/` — Python hardware control (legacy, moving to ESP32)

## When Editing
1. Read the file's header comment first
2. Keep the header comment up to date if you change the file's purpose
3. Follow existing patterns in the codebase
