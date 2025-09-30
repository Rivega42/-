# RFID Reader Dashboard

## Overview

This is a full-stack RFID reader dashboard application built with React, Express, and TypeScript. The application provides real-time monitoring and management of multiple RFID reader types through a web interface. It successfully integrates RRU9816, IQRFID-5102, and ACR1281U-C RFID readers with real-time tag display, connection status, and system logs in a modern dashboard interface.

## Recent Changes (September 2025)

### ✅ RRU9816 Integration Completed
- **Successful Hardware Connection**: RRU9816 v03.01 firmware properly connects via COM port at 57600 baud
- **DLL Integration Resolved**: Fixed function naming issues by using correct RRU9816.dll functions (InventoryBuffer_G2, not SetAntenna/StartBufferInventory)
- **Firmware Compatibility**: Bypassed unsupported SetWorkMode/SetAntennaMultiplexing commands specific to v03.01 firmware
- **Dual-Mode Inventory**: Implemented buffer-first approach with automatic fallback to direct Inventory_G2 mode
- **Tag Detection Working**: Successfully detecting RFID tags with proper EPC parsing and real-time display
- **Windows Compatibility**: Full Windows 10/11 support with .NET 6.0 sidecar bridge

### ✅ IQRFID-5102 Protocol Discovery & Integration Completed
- **Protocol Reverse-Engineered**: Used COM Port Monitor and DLL decompilation to discover actual protocol
- **Correct Protocol Format**: `[LEN][ADR][CMD][DATA...][CRC_LOW][CRC_HIGH]` instead of assumed 0xBB format
- **Baud Rate Corrected**: Changed from 115200 to 57600 baud (confirmed via demo application monitoring)
- **Inventory Command Fixed**: Now using `04 00 01 [CRC]` instead of incorrect `BB 00 22 00 00 22 7E`
- **CRC-16 Implementation**: Added proper CRC calculation matching Basic.dll algorithm (polynomial 0x8408)
- **Response Parsing Updated**: Correctly handles both "no tags" (status 0xFB) and tag data responses
- **EPC Extraction Working**: Properly extracts EPC data from format: `[LEN][ADR][CMD][COUNT][RSSI][EPC_LEN][EPC...][CRC]`

### Technical Breakthrough - IQRFID-5102
- **Problem Solved**: Demo app used Basic.dll (different protocol than assumed UHFReader09 0xBB format)
- **Key Discovery**: IQRFID-5102 uses simple length-prefixed protocol with CRC-16, NOT 0xBB framed protocol
- **COM Port Monitoring**: Captured actual byte sequences from working demo: inventory=`04 00 01 DB 4B`, response=`13 00 01 01 01 0C [EPC] [CRC]`
- **Address Byte**: Uses 0x00 (not 0xFF) for device address in this specific implementation

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React with TypeScript and Vite for build tooling
- **UI Library**: Radix UI components with shadcn/ui design system
- **Styling**: Tailwind CSS with CSS variables for theming
- **State Management**: TanStack Query for server state management
- **Routing**: Wouter for lightweight client-side routing
- **Real-time Communication**: WebSocket connection for live RFID data updates

### Backend Architecture
- **Runtime**: Node.js with Express.js framework
- **Language**: TypeScript with ES modules
- **Database**: PostgreSQL with Drizzle ORM for type-safe database operations
- **Hardware Integration**: SerialPort library for RFID reader communication
- **Real-time Features**: WebSocket server for broadcasting tag reads and status updates
- **Storage Abstraction**: Interface-based storage layer with in-memory fallback

### Data Storage Solutions
- **Primary Database**: PostgreSQL via Neon serverless platform
- **ORM**: Drizzle with schema-first approach and automatic migrations
- **Schema Design**: 
  - RFID tags table with EPC, RSSI, read counts, and timestamps
  - System logs table for application events and errors
- **Fallback Storage**: In-memory storage implementation for development/testing

### Authentication and Authorization
- **Current State**: No authentication implemented
- **Session Management**: Express sessions configured with PostgreSQL store (connect-pg-simple)
- **Architecture Ready**: Session infrastructure in place for future auth implementation

### Hardware Integration
- **Multi-Reader Support**: Successfully integrates RRU9816, IQRFID-5102, and ACR1281U-C RFID readers
- **RRU9816 Sidecar Bridge**: .NET 6.0 C# bridge connects RRU9816.dll to Node.js application via WebSocket (ws://localhost:8081)
- **RFID Communication**: Direct DLL calls for RRU9816, Serial port communication for other readers with configurable baud rates
- **Event-Driven Architecture**: EventEmitter pattern for handling tag reads and status changes
- **Connection Management**: Automatic reconnection and error handling for hardware connections
- **Dual-Mode Inventory**: Buffer mode with automatic fallback to direct polling for maximum compatibility
- **Supported Operations**: Tag inventory scanning, real-time tag detection, connection monitoring, PC/SC support for ACR1281U-C

### Real-time Features
- **WebSocket Server**: Dedicated WebSocket endpoint (/ws) for real-time communication
- **Event Broadcasting**: Real-time updates for tag reads, reader status, and system events
- **Client Synchronization**: Automatic reconnection and state synchronization for WebSocket clients

### API Design
- **RESTful Endpoints**: Standard CRUD operations for tags, logs, and statistics
- **Hardware Control**: API endpoints for connecting to RFID readers and managing inventory scans
- **Data Export**: Endpoints for exporting tag data and system logs
- **Status Monitoring**: Real-time status endpoints for system health and reader connectivity

## External Dependencies

### Database Services
- **Neon PostgreSQL**: Serverless PostgreSQL database hosting
- **Connection**: Database URL-based connection with connection pooling

### Development Tools
- **Replit Integration**: Vite plugins for Replit development environment
- **Build Tools**: ESBuild for server bundling, Vite for client bundling
- **Type Safety**: TypeScript with strict configuration across frontend and backend

### Hardware Dependencies
- **Serial Communication**: @serialport/parser-readline for RFID reader communication  
- **Windows Compatibility**: .NET 6.0 runtime for RRU9816 sidecar bridge
- **DLL Integration**: RRU9816.dll with proper function mapping (InventoryBuffer_G2, GetTagBufferInfo)
- **Supported Platforms**: Cross-platform serial port support for Windows, macOS, and Linux
- **WebSocket Bridge**: ws://localhost:8081 for RRU9816 hardware communication

### Frontend Libraries
- **Component Library**: Comprehensive Radix UI component set with shadcn/ui styling
- **Data Fetching**: TanStack Query for caching and synchronization
- **Styling**: Tailwind CSS with custom design tokens
- **Form Handling**: React Hook Form with Zod validation
- **Date Handling**: date-fns for timestamp formatting

### Backend Libraries
- **Web Framework**: Express.js with TypeScript support
- **Database**: Drizzle ORM with Zod schema validation
- **WebSocket**: ws library for real-time communication
- **Session Storage**: connect-pg-simple for PostgreSQL session store