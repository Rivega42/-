import type { Express } from "express";
import { createServer, type Server } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { storage } from "./storage";
import { rfidService } from "./services/rfidService";
import type { WebSocketMessage, TagReadEvent, RfidReaderStatus, SystemLog } from "@shared/schema";

export async function registerRoutes(app: Express): Promise<Server> {
  const httpServer = createServer(app);

  // WebSocket server on /ws path
  const wss = new WebSocketServer({ server: httpServer, path: '/ws' });

  // Store active WebSocket connections
  const clients = new Set<WebSocket>();

  // Broadcast to all connected clients
  const broadcast = (message: WebSocketMessage) => {
    const messageStr = JSON.stringify(message);
    clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(messageStr);
      }
    });
  };

  // RFID Service event handlers
  rfidService.on('tagRead', (tagEvent: TagReadEvent) => {
    broadcast({
      type: 'tag_read',
      data: tagEvent,
    });
  });

  rfidService.on('status', (status: RfidReaderStatus) => {
    broadcast({
      type: 'reader_status',
      data: status,
    });
  });

  // WebSocket connection handler
  wss.on('connection', (ws) => {
    clients.add(ws);
    console.log('WebSocket client connected');

    // Send current status to new client
    const currentStatus = rfidService.getConnectionStatus();
    ws.send(JSON.stringify({
      type: 'reader_status',
      data: currentStatus,
    }));

    ws.on('close', () => {
      clients.delete(ws);
      console.log('WebSocket client disconnected');
    });

    ws.on('error', (error) => {
      console.error('WebSocket error:', error);
      clients.delete(ws);
    });
  });

  // REST API routes
  
  // Get available COM ports
  app.get("/api/ports", async (req, res) => {
    try {
      const ports = await rfidService.getAvailablePorts();
      res.json({ ports });
    } catch (error) {
      res.status(500).json({ 
        error: error instanceof Error ? error.message : 'Failed to get ports' 
      });
    }
  });

  // Connect to RFID reader
  app.post("/api/connect", async (req, res) => {
    try {
      const { port, baudRate = 57600 } = req.body;
      
      if (!port) {
        return res.status(400).json({ error: 'Port is required' });
      }

      await rfidService.connect(port, baudRate);
      res.json({ success: true, message: 'Connected successfully' });
    } catch (error) {
      res.status(500).json({ 
        error: error instanceof Error ? error.message : 'Failed to connect' 
      });
    }
  });

  // Disconnect from RFID reader
  app.post("/api/disconnect", async (req, res) => {
    try {
      await rfidService.disconnect();
      res.json({ success: true, message: 'Disconnected successfully' });
    } catch (error) {
      res.status(500).json({ 
        error: error instanceof Error ? error.message : 'Failed to disconnect' 
      });
    }
  });

  // Start manual inventory
  app.post("/api/inventory", async (req, res) => {
    try {
      rfidService.manualInventory();
      res.json({ success: true, message: 'Inventory started' });
    } catch (error) {
      res.status(500).json({ 
        error: error instanceof Error ? error.message : 'Failed to start inventory' 
      });
    }
  });

  // Get all RFID tags
  app.get("/api/tags", async (req, res) => {
    try {
      const tags = await storage.getAllRfidTags();
      res.json(tags);
    } catch (error) {
      res.status(500).json({ 
        error: error instanceof Error ? error.message : 'Failed to get tags' 
      });
    }
  });

  // Clear all RFID tags
  app.delete("/api/tags", async (req, res) => {
    try {
      await storage.clearAllRfidTags();
      res.json({ success: true, message: 'All tags cleared' });
    } catch (error) {
      res.status(500).json({ 
        error: error instanceof Error ? error.message : 'Failed to clear tags' 
      });
    }
  });

  // Get system logs
  app.get("/api/logs", async (req, res) => {
    try {
      const logs = await storage.getAllSystemLogs();
      res.json(logs);
    } catch (error) {
      res.status(500).json({ 
        error: error instanceof Error ? error.message : 'Failed to get logs' 
      });
    }
  });

  // Clear system logs
  app.delete("/api/logs", async (req, res) => {
    try {
      await storage.clearSystemLogs();
      res.json({ success: true, message: 'Logs cleared' });
    } catch (error) {
      res.status(500).json({ 
        error: error instanceof Error ? error.message : 'Failed to clear logs' 
      });
    }
  });

  // Get statistics
  app.get("/api/statistics", async (req, res) => {
    try {
      const stats = await storage.getStatistics();
      res.json(stats);
      
      // Also broadcast via WebSocket
      broadcast({
        type: 'statistics',
        data: stats,
      });
    } catch (error) {
      res.status(500).json({ 
        error: error instanceof Error ? error.message : 'Failed to get statistics' 
      });
    }
  });

  // TEMPORARY: Simulate RFID tag reading for testing (remove in production)
  app.post("/api/simulate-tag-read", async (req, res) => {
    try {
      const { epc, rssi, timestamp } = req.body;
      
      if (!epc) {
        return res.status(400).json({ error: 'EPC is required' });
      }

      // Store in database
      const tag = await storage.createOrUpdateRfidTag({
        epc,
        rssi: rssi?.toString() || '-50',
      });

      // Emit tag read event
      const tagEvent = {
        epc: tag.epc,
        rssi: parseFloat(tag.rssi || '0'),
        timestamp: timestamp || new Date().toISOString(),
      };

      broadcast({
        type: 'tag_read',
        data: tagEvent,
      });

      // Add system log
      await storage.addSystemLog({
        level: 'INFO',
        message: `Simulated tag read: ${epc}, RSSI: ${rssi || -50} dBm`,
      });

      res.json({ success: true, message: 'Tag simulated successfully', tag });
    } catch (error) {
      res.status(500).json({ 
        error: error instanceof Error ? error.message : 'Failed to simulate tag' 
      });
    }
  });

  // Periodically broadcast statistics
  setInterval(async () => {
    try {
      const stats = await storage.getStatistics();
      broadcast({
        type: 'statistics',
        data: stats,
      });
    } catch (error) {
      console.error('Error broadcasting statistics:', error);
    }
  }, 5000); // Every 5 seconds

  return httpServer;
}
