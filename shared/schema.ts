import { sql } from "drizzle-orm";
import { pgTable, text, varchar, timestamp, integer, decimal, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// ==================== ЯЧЕЙКИ ШКАФА (126 ячеек) ====================
export const cells = pgTable("cells", {
  id: integer("id").primaryKey(),
  row: text("row").notNull(), // 'FRONT' | 'BACK'
  x: integer("x").notNull(), // 0-2 (колонки)
  y: integer("y").notNull(), // 0-20 (позиции)
  status: text("status").notNull().default('empty'), // 'empty' | 'occupied' | 'blocked' | 'reserved'
  bookRfid: text("book_rfid"),
  bookTitle: text("book_title"),
  reservedFor: text("reserved_for"), // user RFID
  needsExtraction: boolean("needs_extraction").default(false),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertCellSchema = createInsertSchema(cells).omit({ id: true, updatedAt: true });
export type InsertCell = z.infer<typeof insertCellSchema>;
export type Cell = typeof cells.$inferSelect;

// ==================== ПОЛЬЗОВАТЕЛИ ====================
export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  rfid: text("rfid").notNull().unique(),
  name: text("name").notNull(),
  role: text("role").notNull().default('reader'), // 'reader' | 'librarian' | 'admin'
  email: text("email"),
  phone: text("phone"),
  blocked: boolean("blocked").default(false),
  createdAt: timestamp("created_at").defaultNow(),
});

export const insertUserSchema = createInsertSchema(users).omit({ id: true, createdAt: true });
export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;

// ==================== КНИГИ ====================
export const books = pgTable("books", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  rfid: text("rfid").notNull().unique(),
  title: text("title").notNull(),
  author: text("author"),
  isbn: text("isbn"),
  status: text("status").notNull().default('available'), // 'available' | 'in_cabinet' | 'issued' | 'reserved'
  reservedForRfid: text("reserved_for_rfid"), // user RFID who reserved
  issuedToRfid: text("issued_to_rfid"), // user RFID who has it
  cellId: integer("cell_id"), // which cell it's in
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertBookSchema = createInsertSchema(books).omit({ id: true, createdAt: true, updatedAt: true });
export type InsertBook = z.infer<typeof insertBookSchema>;
export type Book = typeof books.$inferSelect;

// ==================== ОПЕРАЦИИ ====================
export const operations = pgTable("operations", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  timestamp: timestamp("timestamp").defaultNow(),
  operation: text("operation").notNull(), // 'INIT' | 'TAKE' | 'GIVE' | 'ISSUE' | 'RETURN' | 'LOAD' | 'UNLOAD'
  cellRow: text("cell_row"),
  cellX: integer("cell_x"),
  cellY: integer("cell_y"),
  bookRfid: text("book_rfid"),
  userRfid: text("user_rfid"),
  result: text("result").notNull().default('OK'), // 'OK' | 'ERROR'
  errorMessage: text("error_message"),
  durationMs: integer("duration_ms"),
});

export const insertOperationSchema = createInsertSchema(operations).omit({ id: true, timestamp: true });
export type InsertOperation = z.infer<typeof insertOperationSchema>;
export type Operation = typeof operations.$inferSelect;

// ==================== СИСТЕМНЫЕ ЛОГИ ====================
export const systemLogs = pgTable("system_logs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  level: text("level").notNull(), // 'INFO' | 'SUCCESS' | 'ERROR' | 'WARNING'
  message: text("message").notNull(),
  component: text("component"), // 'MOTOR' | 'SENSOR' | 'RFID' | 'IRBIS' | 'SYSTEM'
  timestamp: timestamp("timestamp").notNull().defaultNow(),
});

export const insertSystemLogSchema = createInsertSchema(systemLogs).omit({ id: true, timestamp: true });
export type InsertSystemLog = z.infer<typeof insertSystemLogSchema>;
export type SystemLog = typeof systemLogs.$inferSelect;

// ==================== НАСТРОЙКИ СИСТЕМЫ ====================
export const settings = pgTable("settings", {
  key: text("key").primaryKey(),
  value: text("value").notNull(),
  description: text("description"),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertSettingSchema = createInsertSchema(settings).omit({ updatedAt: true });
export type InsertSetting = z.infer<typeof insertSettingSchema>;
export type Setting = typeof settings.$inferSelect;

// ==================== КАЛИБРОВОЧНЫЕ ДАННЫЕ ====================
export interface CalibrationData {
  kinematics: {
    x_plus_dir_a: number;
    x_plus_dir_b: number;
    y_plus_dir_a: number;
    y_plus_dir_b: number;
  };
  positions: {
    x: number[];
    y: number[];
  };
  window: {
    x: number;
    y: number;
  };
  grab_front: {
    extend1: number;
    retract: number;
    extend2: number;
  };
  grab_back: {
    extend1: number;
    retract: number;
    extend2: number;
  };
  speeds: {
    xy: number;
    tray: number;
    acceleration: number;
  };
  servos: {
    lock1_open: number;
    lock1_close: number;
    lock2_open: number;
    lock2_close: number;
  };
}

// ==================== СИСТЕМА СОСТОЯНИЕ ====================
export interface SystemStatus {
  state: 'idle' | 'busy' | 'error' | 'maintenance' | 'initializing';
  currentOperation?: string;
  position: {
    x: number;
    y: number;
    tray: number;
  };
  sensors: {
    x_begin: boolean;
    x_end: boolean;
    y_begin: boolean;
    y_end: boolean;
    tray_begin: boolean;
    tray_end: boolean;
  };
  shutters: {
    inner: boolean; // true = open
    outer: boolean;
  };
  locks: {
    front: boolean; // true = open
    back: boolean;
  };
  irbisConnected: boolean;
  autonomousMode: boolean;
  maintenanceMode: boolean;
  lastError?: string;
}

// ==================== RFID ТЕГИ (из старой схемы) ====================
export const rfidTags = pgTable("rfid_tags", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  epc: text("epc").notNull().unique(),
  rssi: decimal("rssi", { precision: 5, scale: 2 }),
  readCount: integer("read_count").notNull().default(1),
  firstSeen: timestamp("first_seen").notNull().defaultNow(),
  lastSeen: timestamp("last_seen").notNull().defaultNow(),
});

export const insertRfidTagSchema = createInsertSchema(rfidTags).omit({ id: true, firstSeen: true, lastSeen: true });
export type InsertRfidTag = z.infer<typeof insertRfidTagSchema>;
export type RfidTag = typeof rfidTags.$inferSelect;

// ==================== ТИПЫ RFID СЧИТЫВАТЕЛЕЙ ====================
export enum ReaderType {
  RRU9816 = 'RRU9816',
  IQRFID5102 = 'IQRFID-5102',
  ACR1281UC = 'ACR1281U-C'
}

export interface ReaderConfig {
  type: ReaderType;
  port?: string;
  baudRate?: number;
  description: string;
  protocol: string;
  frequency: string;
}

// ==================== WebSocket СООБЩЕНИЯ ====================
export interface RfidReaderStatus {
  connected: boolean;
  readerType?: ReaderType;
  port?: string;
  error?: string;
}

export interface TagReadEvent {
  epc: string;
  rssi: number;
  timestamp: string;
  readerType?: ReaderType;
}

export interface CardReadEvent {
  uid: string;
  cardType: 'library' | 'ekp';
  timestamp: string;
}

export interface ProgressEvent {
  step: number;
  total: number;
  message: string;
  operation: string;
}

export interface SensorEvent {
  sensors: SystemStatus['sensors'];
  timestamp: string;
}

export interface PositionEvent {
  x: number;
  y: number;
  tray: number;
  timestamp: string;
}

export interface CabinetState {
  state: 'idle' | 'moving' | 'busy' | 'error' | 'maintenance';
  position: { x: number; y: number; row: string };
  trayOpen: boolean;
  bookOnTray: string | null;
  sensors: {
    tray_sensor: boolean;
    book_sensor: boolean;
    door_closed: boolean;
    emergency_stop: boolean;
  };
  currentOperation: string | null;
  lastError: string | null;
}

export type WebSocketMessage = 
  | { type: 'tag_read'; data: TagReadEvent }
  | { type: 'card_read'; data: CardReadEvent }
  | { type: 'reader_status'; data: RfidReaderStatus }
  | { type: 'log_entry'; data: SystemLog }
  | { type: 'progress'; data: ProgressEvent }
  | { type: 'sensors'; data: SensorEvent }
  | { type: 'position'; data: PositionEvent }
  | { type: 'status'; data: SystemStatus }
  | { type: 'statistics'; data: Statistics }
  | { type: 'cabinet_state'; data: CabinetState }
  | { type: 'operation_started'; data: any }
  | { type: 'operation_completed'; data: any }
  | { type: 'operation_failed'; data: any }
  | { type: 'cell_opened'; data: any }
  | { type: 'book_detected'; data: { rfid: string } };

// ==================== СТАТИСТИКА ====================
export interface Statistics {
  totalReads: number;
  uniqueTags: number;
  readRate: number;
  issuesTotal: number;
  issuesToday: number;
  returnsTotal: number;
  returnsToday: number;
  occupiedCells: number;
  totalCells: number;
  booksNeedExtraction: number;
}

// ==================== РОЛИ И ПРАВА ====================
export type UserRole = 'reader' | 'librarian' | 'admin';

export const ROLE_PERMISSIONS = {
  reader: ['issue', 'return'],
  librarian: ['issue', 'return', 'load', 'unload', 'inventory'],
  admin: ['issue', 'return', 'load', 'unload', 'inventory', 'calibrate', 'settings', 'maintenance'],
} as const;

// ==================== ЗАБЛОКИРОВАННЫЕ ЯЧЕЙКИ ====================
export const BLOCKED_CELLS = {
  FRONT: [
    { x: 1, y: 7 }, { x: 1, y: 8 }, { x: 1, y: 9 }, { x: 1, y: 10 },
    { x: 1, y: 11 }, { x: 1, y: 12 }, { x: 1, y: 13 }, { x: 1, y: 14 },
    { x: 1, y: 15 }, { x: 1, y: 16 }, { x: 1, y: 17 }, { x: 1, y: 18 },
  ],
  BACK: [
    { x: 0, y: 19 }, { x: 0, y: 20 },
    { x: 1, y: 19 }, { x: 1, y: 20 },
    { x: 2, y: 20 },
  ],
};

// ==================== ОКНО ВЫДАЧИ ====================
export const WINDOW_POSITION = { row: 'FRONT', x: 1, y: 9 };
