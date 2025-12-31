# RFID Reader Dashboard

## Overview
This project is a local Windows web application designed to integrate and manage multiple RFID readers of different types in real-time via a web interface accessible on localhost. It supports three primary RFID reader types: RRU9816 (UHF), IQRFID-5102 (UHF), and ACR1281U-C (NFC/HF). The application provides monitoring and control functionalities, offering a unified dashboard for various RFID technologies. The business vision is to provide a versatile and robust solution for RFID tag tracking and data acquisition in various industrial and commercial settings.

## User Preferences
Preferred communication style: Simple, everyday language (Русский).

## System Architecture

### UI/UX Decisions
The frontend is built using React 18, TypeScript, Vite, and TailwindCSS, providing a modern and responsive user interface. shadcn/ui and Radix UI are used for UI components, ensuring a consistent and accessible design. TanStack Query handles data caching and synchronization, while Wouter manages routing. Real-time updates are facilitated via WebSockets.

### Technical Implementations
The system is divided into a frontend (React), a backend (Express.js on Node.js), and a C# sidecar for specific reader integrations.

**Reader Integration Details:**
-   **RRU9816 (UHF RFID Reader):** Communicates via a C# Sidecar using WebSockets, which in turn interacts with a `RRU9816.dll` through a COM Port. It supports both buffer and direct inventory modes.
-   **IQRFID-5102 (UHF RFID Reader):** Connects directly to the Node.js backend via a Serial Port. Communication uses a custom binary protocol with CRC-16 for data integrity, employing a polling mechanism.
-   **ACR1281U-C (NFC/HF Reader):** Integrates with the Node.js backend through the PC/SC API, leveraging the Windows Smart Card Service for USB-connected readers. This reader operates on an event-driven model, automatically detecting cards.

**Core Features:**
-   Real-time display of read tags and system logs on the dashboard.
-   API endpoints for managing reader connections, status, tags, and logs.
-   In-memory storage for session-based tag and log data (no persistent database).

**Interaction Patterns:**
| Parameter | RRU9816 | IQRFID-5102 | ACR1281U-C |
|-----------|---------|-------------|------------|
| **Transport** | WebSocket + DLL | Serial Port | PC/SC API |
| **Data Format** | JSON | Binary + CRC | PC/SC Events |
| **Operating Modes** | Buffer + Direct | Direct polling | Event-driven |

### System Design Choices
The backend utilizes Express.js with TypeScript, providing a robust API layer and managing WebSocket connections for real-time data push to the frontend. An `RfidService` centralizes reader management, abstracting the communication differences between various reader types using an `EventEmitter` for tag events. The C# sidecar for RRU9816 acts as a bridge, translating WebSocket commands from Node.js into DLL calls for hardware interaction.

### Project Structure
-   `/client`: Frontend React application.
-   `/server`: Node.js Express backend.
-   `/rru9816-sidecar`: C# bridge application for RRU9816.
-   `/shared`: Shared TypeScript types and schemas.

## External Dependencies

-   **RRU9816 Reader:** Requires .NET 6.0 Runtime for the C# Sidecar and the proprietary `RRU9816.dll` for hardware interaction.
-   **IQRFID-5102 Reader:** Uses the `serialport` Node.js library for direct serial communication.
-   **ACR1281U-C Reader:** Relies on the Windows Smart Card Service (PC/SC API) for communication.
-   **Frontend:** React 18, TypeScript, Vite, TailwindCSS, shadcn/ui, Radix UI, TanStack Query, Wouter, WebSocket API.
-   **Backend:** Node.js, Express.js, TypeScript, `ws` (WebSocket library), `serialport` (for IQRFID-5102), `EventEmitter`.