# RFID Reader Dashboard

## Overview

This is a full-stack RFID reader dashboard application built with React, Express, and TypeScript. The application provides real-time monitoring and management of RFID tag readings through a web interface. It connects to RFID hardware via serial port communication and displays tag data, connection status, and system logs in a modern dashboard interface.

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
- **RFID Communication**: Serial port communication with configurable baud rates
- **Event-Driven Architecture**: EventEmitter pattern for handling tag reads and status changes
- **Connection Management**: Automatic reconnection and error handling for serial connections
- **Supported Operations**: Tag inventory scanning, real-time tag detection, connection monitoring

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
- **Supported Platforms**: Cross-platform serial port support for Windows, macOS, and Linux

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