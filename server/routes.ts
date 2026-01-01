import type { Express } from "express";
import { createServer, type Server } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { storage } from "./storage";
import { rfidService } from "./services/rfidService";
import { cabinetService } from "./services/cabinetService";
import { irbisService } from "./services/irbisService";
import type { 
  WebSocketMessage, TagReadEvent, RfidReaderStatus, SystemLog,
  SystemStatus, User, Cell, Book, CalibrationData
} from "@shared/schema";
import { ReaderType } from "@shared/schema";

// Состояние системы (будет управляться механикой)
let systemStatus: SystemStatus = {
  state: 'idle',
  position: { x: 0, y: 0, tray: 0 },
  sensors: {
    x_begin: true,
    x_end: false,
    y_begin: true,
    y_end: false,
    tray_begin: true,
    tray_end: false,
  },
  shutters: { inner: false, outer: false },
  locks: { front: false, back: false },
  irbisConnected: false,
  autonomousMode: true,
  maintenanceMode: false,
};

// Текущая сессия авторизации
let currentSession: { user: User | null; expiresAt: Date | null } = {
  user: null,
  expiresAt: null,
};

export async function registerRoutes(app: Express): Promise<Server> {
  const httpServer = createServer(app);
  const wss = new WebSocketServer({ server: httpServer, path: '/ws' });
  const clients = new Set<WebSocket>();

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
    broadcast({ type: 'tag_read', data: tagEvent });
  });

  rfidService.on('status', (status: RfidReaderStatus) => {
    broadcast({ type: 'reader_status', data: status });
  });

  // Cabinet Service event handlers
  cabinetService.on('state_changed', (state) => {
    broadcast({ type: 'cabinet_state', data: state });
  });

  cabinetService.on('operation_started', (data) => {
    broadcast({ type: 'operation_started', data });
  });

  cabinetService.on('operation_completed', (data) => {
    broadcast({ type: 'operation_completed', data });
  });

  cabinetService.on('operation_failed', (data) => {
    broadcast({ type: 'operation_failed', data });
  });

  cabinetService.on('cell_opened', (position) => {
    broadcast({ type: 'cell_opened', data: position });
  });

  cabinetService.on('book_detected', (rfid) => {
    broadcast({ type: 'book_detected', data: { rfid } });
  });

  // WebSocket connection handler
  wss.on('connection', (ws) => {
    clients.add(ws);
    console.log('WebSocket client connected');

    ws.send(JSON.stringify({ type: 'status', data: systemStatus }));
    ws.send(JSON.stringify({ type: 'reader_status', data: rfidService.getConnectionStatus() }));

    ws.on('message', async (data) => {
      try {
        const message = JSON.parse(data.toString());
        await handleWebSocketMessage(message, ws, broadcast);
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    });

    ws.on('close', () => {
      clients.delete(ws);
      console.log('WebSocket client disconnected');
    });

    ws.on('error', (error) => {
      console.error('WebSocket error:', error);
      clients.delete(ws);
    });
  });

  // ==================== СИСТЕМА ====================
  
  app.get("/api/status", (req, res) => {
    res.json(systemStatus);
  });

  app.post("/api/maintenance", async (req, res) => {
    const { enabled } = req.body;
    systemStatus.maintenanceMode = Boolean(enabled);
    broadcast({ type: 'status', data: systemStatus });
    await storage.addSystemLog({
      level: enabled ? 'WARNING' : 'INFO',
      message: enabled ? 'Режим обслуживания включён' : 'Режим обслуживания отключён',
      component: 'SYSTEM',
    });
    res.json({ success: true, maintenanceMode: systemStatus.maintenanceMode });
  });

  // ==================== ЯЧЕЙКИ ====================

  app.get("/api/cells", async (req, res) => {
    try {
      const cells = await storage.getAllCells();
      res.json(cells);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get cells' });
    }
  });

  // Специфичные роуты ПЕРЕД параметризованными
  app.get("/api/cells/extraction", async (req, res) => {
    try {
      const cells = await storage.getCellsNeedingExtraction();
      res.json(cells);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get cells' });
    }
  });

  app.get("/api/cells/available/:row?", async (req, res) => {
    try {
      const cells = await storage.getAvailableCells(req.params.row);
      res.json(cells);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get available cells' });
    }
  });

  // Параметризованные роуты ПОСЛЕ специфичных
  app.get("/api/cells/:id", async (req, res) => {
    try {
      const cell = await storage.getCell(parseInt(req.params.id));
      if (!cell) return res.status(404).json({ error: 'Cell not found' });
      res.json(cell);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get cell' });
    }
  });

  app.patch("/api/cells/:id", async (req, res) => {
    try {
      const cell = await storage.updateCell(parseInt(req.params.id), req.body);
      if (!cell) return res.status(404).json({ error: 'Cell not found' });
      res.json(cell);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to update cell' });
    }
  });

  // ==================== ПОЛЬЗОВАТЕЛИ ====================

  app.get("/api/users", async (req, res) => {
    try {
      const users = await storage.getAllUsers();
      res.json(users);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get users' });
    }
  });

  app.get("/api/users/:id", async (req, res) => {
    try {
      const user = await storage.getUser(req.params.id);
      if (!user) return res.status(404).json({ error: 'User not found' });
      res.json(user);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get user' });
    }
  });

  app.get("/api/users/rfid/:rfid", async (req, res) => {
    try {
      const user = await storage.getUserByRfid(req.params.rfid);
      if (!user) return res.status(404).json({ error: 'User not found' });
      res.json(user);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get user' });
    }
  });

  app.post("/api/users", async (req, res) => {
    try {
      const user = await storage.createUser(req.body);
      res.status(201).json(user);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to create user' });
    }
  });

  // ==================== КНИГИ ====================

  app.get("/api/books", async (req, res) => {
    try {
      const books = await storage.getAllBooks();
      res.json(books);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get books' });
    }
  });

  app.get("/api/books/:id", async (req, res) => {
    try {
      const book = await storage.getBook(req.params.id);
      if (!book) return res.status(404).json({ error: 'Book not found' });
      res.json(book);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get book' });
    }
  });

  app.get("/api/books/rfid/:rfid", async (req, res) => {
    try {
      const book = await storage.getBookByRfid(req.params.rfid);
      if (!book) return res.status(404).json({ error: 'Book not found' });
      res.json(book);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get book' });
    }
  });

  app.get("/api/books/reserved/:userRfid", async (req, res) => {
    try {
      const books = await storage.getReservedBooks(req.params.userRfid);
      res.json(books);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get reserved books' });
    }
  });

  app.post("/api/books", async (req, res) => {
    try {
      const book = await storage.createBook(req.body);
      res.status(201).json(book);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to create book' });
    }
  });

  app.patch("/api/books/:id", async (req, res) => {
    try {
      const book = await storage.updateBook(req.params.id, req.body);
      if (!book) return res.status(404).json({ error: 'Book not found' });
      res.json(book);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to update book' });
    }
  });

  // ==================== ОПЕРАЦИИ ====================

  app.get("/api/operations", async (req, res) => {
    try {
      const limit = req.query.limit ? parseInt(req.query.limit as string) : undefined;
      const operations = await storage.getAllOperations(limit);
      res.json(operations);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get operations' });
    }
  });

  app.get("/api/operations/today", async (req, res) => {
    try {
      const operations = await storage.getOperationsToday();
      res.json(operations);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get operations' });
    }
  });

  app.post("/api/operations", async (req, res) => {
    try {
      const operation = await storage.createOperation(req.body);
      res.status(201).json(operation);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to create operation' });
    }
  });

  // ==================== АВТОРИЗАЦИЯ ====================

  app.post("/api/auth/card", async (req, res) => {
    try {
      const { rfid } = req.body;
      if (!rfid) return res.status(400).json({ error: 'RFID is required' });

      if (systemStatus.maintenanceMode) {
        return res.status(503).json({ error: 'Шкаф временно недоступен' });
      }

      const user = await storage.getUserByRfid(rfid);
      if (!user) {
        await storage.addSystemLog({
          level: 'WARNING',
          message: `Неизвестная карта: ${rfid}`,
          component: 'RFID',
        });
        return res.status(404).json({ error: 'Карта не зарегистрирована' });
      }

      if (user.blocked) {
        return res.status(403).json({ error: 'Обратитесь к библиотекарю' });
      }

      currentSession = {
        user,
        expiresAt: new Date(Date.now() + 5 * 60 * 1000), // 5 минут
      };

      await storage.addSystemLog({
        level: 'INFO',
        message: `Авторизация: ${user.name} (${user.role})`,
        component: 'SYSTEM',
      });

      broadcast({ type: 'card_read', data: { uid: rfid, cardType: 'library', timestamp: new Date().toISOString() } });

      const reservedBooks = await storage.getReservedBooks(rfid);
      const needsExtraction = await storage.getCellsNeedingExtraction();

      res.json({ 
        success: true, 
        user,
        reservedBooks,
        needsExtraction: needsExtraction.length,
      });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Auth failed' });
    }
  });

  app.post("/api/auth/logout", (req, res) => {
    currentSession = { user: null, expiresAt: null };
    res.json({ success: true });
  });

  app.get("/api/auth/session", (req, res) => {
    if (!currentSession.user || !currentSession.expiresAt || currentSession.expiresAt < new Date()) {
      currentSession = { user: null, expiresAt: null };
      return res.json({ authenticated: false });
    }
    res.json({ authenticated: true, user: currentSession.user });
  });

  // ==================== БИЗНЕС-ОПЕРАЦИИ ====================

  app.post("/api/issue", async (req, res) => {
    try {
      const { bookRfid, userRfid } = req.body;
      if (!bookRfid || !userRfid) {
        return res.status(400).json({ error: 'bookRfid and userRfid are required' });
      }

      const book = await storage.getBookByRfid(bookRfid);
      if (!book) return res.status(404).json({ error: 'Book not found' });
      
      if (book.reservedForRfid && book.reservedForRfid !== userRfid) {
        return res.status(403).json({ error: 'Книга забронирована другим читателем' });
      }

      const startTime = Date.now();

      // Обновляем книгу
      await storage.updateBook(book.id, {
        status: 'issued',
        issuedToRfid: userRfid,
        reservedForRfid: null,
        cellId: null,
      });

      // Очищаем ячейку
      if (book.cellId !== null) {
        await storage.updateCell(book.cellId, {
          status: 'empty',
          bookRfid: null,
          bookTitle: null,
          reservedFor: null,
        });
      }

      // Записываем операцию
      const cell = book.cellId !== null ? await storage.getCell(book.cellId) : null;
      await storage.createOperation({
        operation: 'ISSUE',
        cellRow: cell?.row,
        cellX: cell?.x,
        cellY: cell?.y,
        bookRfid,
        userRfid,
        result: 'OK',
        durationMs: Date.now() - startTime,
      });

      await storage.addSystemLog({
        level: 'SUCCESS',
        message: `Выдана книга: ${book.title}`,
        component: 'SYSTEM',
      });

      res.json({ success: true, book });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Issue failed' });
    }
  });

  app.post("/api/return", async (req, res) => {
    try {
      const { bookRfid, userRfid } = req.body;
      if (!bookRfid) return res.status(400).json({ error: 'bookRfid is required' });

      const book = await storage.getBookByRfid(bookRfid);
      if (!book) return res.status(404).json({ error: 'Book not found' });

      const startTime = Date.now();

      // Находим свободную ячейку
      const availableCells = await storage.getAvailableCells();
      if (availableCells.length === 0) {
        return res.status(503).json({ error: 'Нет свободных ячеек' });
      }

      const targetCell = availableCells[0];

      // Обновляем ячейку
      await storage.updateCell(targetCell.id, {
        status: 'occupied',
        bookRfid,
        bookTitle: book.title,
        needsExtraction: true,
      });

      // Обновляем книгу
      await storage.updateBook(book.id, {
        status: 'in_cabinet',
        issuedToRfid: null,
        cellId: targetCell.id,
      });

      await storage.createOperation({
        operation: 'RETURN',
        cellRow: targetCell.row,
        cellX: targetCell.x,
        cellY: targetCell.y,
        bookRfid,
        userRfid,
        result: 'OK',
        durationMs: Date.now() - startTime,
      });

      await storage.addSystemLog({
        level: 'SUCCESS',
        message: `Возвращена книга: ${book.title}`,
        component: 'SYSTEM',
      });

      res.json({ success: true, book, cell: targetCell });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Return failed' });
    }
  });

  // ==================== ОПЕРАЦИИ БИБЛИОТЕКАРЯ ====================

  app.post("/api/reserve", async (req, res) => {
    try {
      const { bookRfid, userRfid } = req.body;
      if (!bookRfid || !userRfid) {
        return res.status(400).json({ error: 'bookRfid and userRfid are required' });
      }

      const result = await cabinetService.reserveBook(bookRfid, userRfid);
      if (!result.success) {
        return res.status(400).json({ error: result.message });
      }

      res.json(result);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Reserve failed' });
    }
  });

  app.post("/api/cancel-reservation", async (req, res) => {
    try {
      const { bookRfid, userRfid } = req.body;
      if (!bookRfid || !userRfid) {
        return res.status(400).json({ error: 'bookRfid and userRfid are required' });
      }

      const result = await cabinetService.cancelReservation(bookRfid, userRfid);
      if (!result.success) {
        return res.status(400).json({ error: result.message });
      }

      res.json(result);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Cancel reservation failed' });
    }
  });

  app.post("/api/load-book", async (req, res) => {
    try {
      const { bookRfid, title, author } = req.body;
      if (!bookRfid || !title) {
        return res.status(400).json({ error: 'bookRfid and title are required' });
      }

      const result = await cabinetService.loadBook(bookRfid, title, author);
      if (!result.success) {
        return res.status(400).json({ error: result.message });
      }

      res.json(result);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Load book failed' });
    }
  });

  app.post("/api/extract", async (req, res) => {
    try {
      const { cellId } = req.body;
      if (cellId === undefined) {
        return res.status(400).json({ error: 'cellId is required' });
      }

      const result = await cabinetService.extractBook(cellId);
      if (!result.success) {
        return res.status(400).json({ error: result.message });
      }

      res.json(result);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Extract failed' });
    }
  });

  app.post("/api/extract-all", async (req, res) => {
    try {
      const result = await cabinetService.extractAllReturned();
      res.json(result);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Extract all failed' });
    }
  });

  app.post("/api/run-inventory", async (req, res) => {
    try {
      const result = await cabinetService.runInventory();
      res.json(result);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Inventory failed' });
    }
  });

  app.get("/api/cabinet/state", (req, res) => {
    try {
      const state = cabinetService.getState();
      res.json(state);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Get state failed' });
    }
  });

  app.post("/api/cabinet/clear-error", (req, res) => {
    try {
      cabinetService.clearError();
      res.json({ success: true });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Clear error failed' });
    }
  });

  // ==================== RFID (существующие) ====================

  app.get("/api/ports", async (req, res) => {
    try {
      const ports = await rfidService.getAvailablePorts();
      res.json({ ports });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get ports' });
    }
  });

  app.get("/api/reader-configs", (req, res) => {
    try {
      const configs = rfidService.getReaderConfigs();
      res.json({ configs });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get reader configs' });
    }
  });

  app.post("/api/connect", async (req, res) => {
    try {
      const { port, readerType, baudRate } = req.body;
      if (!port) return res.status(400).json({ error: 'Port is required' });
      if (!readerType) return res.status(400).json({ error: 'Reader type is required' });
      if (!Object.values(ReaderType).includes(readerType)) {
        return res.status(400).json({ error: 'Invalid reader type' });
      }
      await rfidService.connect(port, readerType, baudRate);
      res.json({ success: true, message: `Connected to ${readerType} successfully` });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to connect' });
    }
  });

  app.post("/api/disconnect", async (req, res) => {
    try {
      await rfidService.disconnect();
      res.json({ success: true, message: 'Disconnected successfully' });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to disconnect' });
    }
  });

  app.post("/api/inventory", async (req, res) => {
    try {
      rfidService.manualInventory();
      res.json({ success: true, message: 'Inventory started' });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to start inventory' });
    }
  });

  // ==================== ТЕГИ И ЛОГИ ====================

  app.get("/api/tags", async (req, res) => {
    try {
      const tags = await storage.getAllRfidTags();
      res.json(tags);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get tags' });
    }
  });

  app.delete("/api/tags", async (req, res) => {
    try {
      await storage.clearAllRfidTags();
      res.json({ success: true, message: 'All tags cleared' });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to clear tags' });
    }
  });

  app.get("/api/logs", async (req, res) => {
    try {
      const limit = req.query.limit ? parseInt(req.query.limit as string) : undefined;
      const logs = await storage.getAllSystemLogs(limit);
      res.json(logs);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get logs' });
    }
  });

  app.delete("/api/logs", async (req, res) => {
    try {
      await storage.clearSystemLogs();
      res.json({ success: true, message: 'Logs cleared' });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to clear logs' });
    }
  });

  app.get("/api/statistics", async (req, res) => {
    try {
      const stats = await storage.getStatistics();
      res.json(stats);
      broadcast({ type: 'statistics', data: stats });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get statistics' });
    }
  });

  app.get("/api/diagnostics", async (req, res) => {
    try {
      const rfidStatus = rfidService.getConnectionStatus();
      
      res.json({
        sensors: systemStatus.sensors,
        motors: systemStatus.state === 'error' ? 'error' : 'ok',
        rfid: {
          cardReader: rfidStatus.connected ? 'connected' : 'disconnected',
          bookReader: 'connected', // Mock: book reader always connected in dev mode
        },
        system: {
          state: systemStatus.state,
          position: systemStatus.position,
          shutters: systemStatus.shutters,
          locks: systemStatus.locks,
          irbisConnected: systemStatus.irbisConnected,
          autonomousMode: systemStatus.autonomousMode,
          maintenanceMode: systemStatus.maintenanceMode,
        }
      });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get diagnostics' });
    }
  });

  // ==================== СИМУЛЯЦИЯ (для тестирования) ====================

  app.post("/api/simulate-tag-read", async (req, res) => {
    try {
      const { epc, rssi, timestamp } = req.body;
      if (!epc) return res.status(400).json({ error: 'EPC is required' });

      const tag = await storage.createOrUpdateRfidTag({
        epc,
        rssi: rssi?.toString() || '-50',
      });

      const tagEvent = {
        epc: tag.epc,
        rssi: parseFloat(tag.rssi || '0'),
        timestamp: timestamp || new Date().toISOString(),
      };

      broadcast({ type: 'tag_read', data: tagEvent });

      await storage.addSystemLog({
        level: 'INFO',
        message: `Simulated tag read: ${epc}, RSSI: ${rssi || -50} dBm`,
        component: 'RFID',
      });

      res.json({ success: true, message: 'Tag simulated successfully', tag });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to simulate tag' });
    }
  });

  app.post("/api/simulate-card-read", async (req, res) => {
    try {
      const { rfid } = req.body;
      if (!rfid) return res.status(400).json({ error: 'RFID is required' });

      broadcast({ 
        type: 'card_read', 
        data: { uid: rfid, cardType: 'library', timestamp: new Date().toISOString() } 
      });

      res.json({ success: true, message: 'Card simulated successfully' });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to simulate card' });
    }
  });

  // ==================== ТЕСТИРОВАНИЕ МЕХАНИКИ ====================

  app.post("/api/test/motor", async (req, res) => {
    try {
      const { command, axis, steps, speed } = req.body;
      
      await storage.addSystemLog({
        level: 'INFO',
        message: `Тест мотора: ${command} ${axis || ''} steps=${steps || 0} speed=${speed || 1000}`,
        component: 'MOTOR',
      });

      // Симуляция движения мотора
      if (command === 'move') {
        const currentPos = systemStatus.position;
        if (axis === 'x') {
          systemStatus.position = { ...currentPos, x: currentPos.x + (steps || 0) };
        } else if (axis === 'y') {
          systemStatus.position = { ...currentPos, y: currentPos.y + (steps || 0) };
        }
        broadcast({ type: 'position', data: { ...systemStatus.position, timestamp: new Date().toISOString() } });
      } else if (command === 'home') {
        systemStatus.position = { x: 0, y: 0, tray: 0 };
        broadcast({ type: 'position', data: { ...systemStatus.position, timestamp: new Date().toISOString() } });
      }

      res.json({ success: true, position: systemStatus.position });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Motor test failed' });
    }
  });

  app.post("/api/test/tray", async (req, res) => {
    try {
      const { command } = req.body;
      
      await storage.addSystemLog({
        level: 'INFO',
        message: `Тест лотка: ${command}`,
        component: 'MOTOR',
      });

      // Симуляция движения лотка
      if (command === 'extend') {
        systemStatus.position = { ...systemStatus.position, tray: 1000 };
      } else if (command === 'retract') {
        systemStatus.position = { ...systemStatus.position, tray: 0 };
      }
      broadcast({ type: 'position', data: { ...systemStatus.position, timestamp: new Date().toISOString() } });

      res.json({ success: true, position: systemStatus.position });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Tray test failed' });
    }
  });

  app.post("/api/test/servo", async (req, res) => {
    try {
      const { servo, command } = req.body;
      
      await storage.addSystemLog({
        level: 'INFO',
        message: `Тест сервопривода: ${servo} ${command}`,
        component: 'SERVO',
      });

      // Симуляция сервопривода
      if (servo === 'lock1' || servo === 'front') {
        systemStatus.locks.front = command === 'open';
      } else if (servo === 'lock2' || servo === 'back') {
        systemStatus.locks.back = command === 'open';
      }
      broadcast({ type: 'status', data: systemStatus });

      res.json({ success: true, locks: systemStatus.locks });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Servo test failed' });
    }
  });

  app.post("/api/test/shutter", async (req, res) => {
    try {
      const { shutter, command } = req.body;
      
      await storage.addSystemLog({
        level: 'INFO',
        message: `Тест шторки: ${shutter} ${command}`,
        component: 'SHUTTER',
      });

      // Симуляция шторки
      if (shutter === 'inner') {
        systemStatus.shutters.inner = command === 'open';
      } else if (shutter === 'outer') {
        systemStatus.shutters.outer = command === 'open';
      }
      broadcast({ type: 'status', data: systemStatus });

      res.json({ success: true, shutters: systemStatus.shutters });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Shutter test failed' });
    }
  });

  app.post("/api/test/sensors", async (req, res) => {
    try {
      await storage.addSystemLog({
        level: 'INFO',
        message: 'Проверка всех датчиков',
        component: 'SENSOR',
      });

      // Симуляция чтения датчиков
      res.json({ 
        success: true, 
        sensors: systemStatus.sensors,
        message: 'Все датчики проверены'
      });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Sensor test failed' });
    }
  });

  // ==================== КАЛИБРОВКА ====================

  const defaultCalibration: CalibrationData = {
    kinematics: { x_plus_dir_a: 1, x_plus_dir_b: -1, y_plus_dir_a: 1, y_plus_dir_b: 1 },
    positions: { 
      x: [0, 5000, 10000], // 3 колонки
      y: [0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000, 9500, 10000] // 21 ряд
    },
    window: { x: 5000, y: 5000 },
    grab_front: { extend1: 1000, retract: 500, extend2: 1500 },
    grab_back: { extend1: 1000, retract: 500, extend2: 1500 },
    speeds: { xy: 3000, tray: 2000, acceleration: 5000 },
    servos: { lock1_open: 90, lock1_close: 0, lock2_open: 90, lock2_close: 0 }
  };

  let calibrationData: CalibrationData = { ...defaultCalibration };

  app.get("/api/calibration", async (req, res) => {
    try {
      res.json(calibrationData);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to get calibration' });
    }
  });

  app.post("/api/calibration", async (req, res) => {
    try {
      const newData = req.body;
      
      // Мержим новые данные с существующими
      calibrationData = {
        ...calibrationData,
        ...newData,
        kinematics: { ...calibrationData.kinematics, ...newData.kinematics },
        positions: { ...calibrationData.positions, ...newData.positions },
        window: { ...calibrationData.window, ...newData.window },
        grab_front: { ...calibrationData.grab_front, ...newData.grab_front },
        grab_back: { ...calibrationData.grab_back, ...newData.grab_back },
        speeds: { ...calibrationData.speeds, ...newData.speeds },
        servos: { ...calibrationData.servos, ...newData.servos },
      };

      await storage.addSystemLog({
        level: 'SUCCESS',
        message: 'Калибровочные данные обновлены',
        component: 'CALIBRATION',
      });

      res.json({ success: true, calibration: calibrationData });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to update calibration' });
    }
  });

  app.post("/api/calibration/reset", async (req, res) => {
    try {
      calibrationData = { ...defaultCalibration };
      
      await storage.addSystemLog({
        level: 'WARNING',
        message: 'Калибровка сброшена к значениям по умолчанию',
        component: 'CALIBRATION',
      });

      res.json({ success: true, calibration: calibrationData });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to reset calibration' });
    }
  });

  // Комплексные тесты калибровки (симуляция в mock режиме)
  app.post("/api/calibration/test-suite", async (req, res) => {
    try {
      const results: {
        test: string;
        status: 'pass' | 'fail' | 'running';
        message: string;
        duration?: number;
      }[] = [];

      const simulateDelay = () => new Promise(resolve => setTimeout(resolve, 100 + Math.random() * 200));

      // 1. Тест моторов - Home
      const startHome = Date.now();
      await simulateDelay();
      systemStatus.position = { x: 0, y: 0, tray: 0 };
      results.push({ 
        test: 'motors_home', 
        status: 'pass', 
        message: 'Перемещение в начальную позицию выполнено',
        duration: Date.now() - startHome
      });

      // 2. Тест лотка - выдвижение/втягивание
      const startTray = Date.now();
      await simulateDelay();
      systemStatus.position.tray = 1000;
      await simulateDelay();
      systemStatus.position.tray = 0;
      results.push({ 
        test: 'tray_cycle', 
        status: 'pass', 
        message: 'Цикл выдвижения/втягивания лотка выполнен',
        duration: Date.now() - startTray
      });

      // 3. Тест сервоприводов - замки
      const startServos = Date.now();
      await simulateDelay();
      systemStatus.locks.front = true;
      await simulateDelay();
      systemStatus.locks.front = false;
      systemStatus.locks.back = true;
      await simulateDelay();
      systemStatus.locks.back = false;
      results.push({ 
        test: 'servos_locks', 
        status: 'pass', 
        message: 'Тест сервоприводов замков пройден',
        duration: Date.now() - startServos
      });

      // 4. Тест шторок
      const startShutters = Date.now();
      await simulateDelay();
      systemStatus.shutters.inner = true;
      await simulateDelay();
      systemStatus.shutters.inner = false;
      systemStatus.shutters.outer = true;
      await simulateDelay();
      systemStatus.shutters.outer = false;
      results.push({ 
        test: 'shutters', 
        status: 'pass', 
        message: 'Тест шторок пройден',
        duration: Date.now() - startShutters
      });

      // 5. Тест датчиков
      const startSensors = Date.now();
      await simulateDelay();
      const allSensorsOk = Object.values(systemStatus.sensors).some(v => v);
      results.push({ 
        test: 'sensors', 
        status: 'pass', 
        message: `Датчики: x_begin=${systemStatus.sensors.x_begin}, y_begin=${systemStatus.sensors.y_begin}`,
        duration: Date.now() - startSensors
      });

      // 6. Тест перемещения к тестовой ячейке
      const startMove = Date.now();
      await simulateDelay();
      systemStatus.position = { x: 1000, y: 1000, tray: 0 };
      await simulateDelay();
      systemStatus.position = { x: 0, y: 0, tray: 0 };
      results.push({ 
        test: 'motors_move', 
        status: 'pass', 
        message: 'Тест перемещения выполнен',
        duration: Date.now() - startMove
      });

      const passed = results.filter(r => r.status === 'pass').length;
      const failed = results.filter(r => r.status === 'fail').length;

      await storage.addSystemLog({
        level: failed > 0 ? 'ERROR' : 'INFO',
        message: `Комплексный тест калибровки: ${passed}/${results.length} пройдено`,
        component: 'CALIBRATION',
      });

      res.json({ 
        success: failed === 0, 
        results,
        summary: { passed, failed, total: results.length }
      });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Failed to run calibration suite' });
    }
  });

  // Отдельные тесты калибровки
  app.post("/api/calibration/test/:testName", async (req, res) => {
    const { testName } = req.params;
    
    try {
      const result: { status: 'pass' | 'fail'; message: string; duration: number } = {
        status: 'pass',
        message: '',
        duration: 0
      };
      const start = Date.now();
      const simulateDelay = () => new Promise(resolve => setTimeout(resolve, 100 + Math.random() * 200));

      switch (testName) {
        case 'home':
          await simulateDelay();
          systemStatus.position = { x: 0, y: 0, tray: 0 };
          result.message = 'Homing выполнен успешно';
          break;
        case 'tray':
          await simulateDelay();
          systemStatus.position.tray = 1000;
          await simulateDelay();
          systemStatus.position.tray = 0;
          result.message = 'Цикл лотка выполнен';
          break;
        case 'servos':
          await simulateDelay();
          systemStatus.locks.front = true;
          await simulateDelay();
          systemStatus.locks.front = false;
          result.message = 'Тест сервоприводов пройден';
          break;
        case 'shutters':
          await simulateDelay();
          systemStatus.shutters.inner = true;
          await simulateDelay();
          systemStatus.shutters.inner = false;
          result.message = 'Тест шторок пройден';
          break;
        case 'sensors':
          await simulateDelay();
          result.message = `Датчики: ${JSON.stringify(systemStatus.sensors)}`;
          break;
        case 'move-cell':
          const { x, y } = req.body;
          await simulateDelay();
          systemStatus.position = { x: x || 2000, y: y || 2000, tray: 0 };
          result.message = `Перемещение к позиции (${x || 2000}, ${y || 2000})`;
          break;
        default:
          throw new Error(`Неизвестный тест: ${testName}`);
      }

      result.duration = Date.now() - start;
      res.json({ success: true, result });
    } catch (error) {
      res.status(500).json({ 
        success: false, 
        result: { 
          status: 'fail', 
          message: error instanceof Error ? error.message : 'Test failed',
          duration: 0
        }
      });
    }
  });

  // Периодическая трансляция статистики
  setInterval(async () => {
    try {
      const stats = await storage.getStatistics();
      broadcast({ type: 'statistics', data: stats });
    } catch (error) {
      console.error('Error broadcasting statistics:', error);
    }
  }, 5000);

  return httpServer;
}

async function handleWebSocketMessage(
  message: any, 
  ws: WebSocket, 
  broadcast: (msg: WebSocketMessage) => void
) {
  switch (message.action) {
    case 'authenticate':
      if (message.card_rfid) {
        const user = await storage.getUserByRfid(message.card_rfid);
        if (user) {
          broadcast({ 
            type: 'card_read', 
            data: { uid: message.card_rfid, cardType: 'library', timestamp: new Date().toISOString() } 
          });
        }
      }
      break;
      
    case 'get_status':
      ws.send(JSON.stringify({ type: 'status', data: systemStatus }));
      break;
      
    default:
      console.log('Unknown WebSocket action:', message.action);
  }
}
