import { sql } from "drizzle-orm";
import { pgTable, text, varchar, timestamp, integer, decimal } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const rfidTags = pgTable("rfid_tags", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  epc: text("epc").notNull().unique(),
  rssi: decimal("rssi", { precision: 5, scale: 2 }),
  readCount: integer("read_count").notNull().default(1),
  firstSeen: timestamp("first_seen").notNull().defaultNow(),
  lastSeen: timestamp("last_seen").notNull().defaultNow(),
});

export const systemLogs = pgTable("system_logs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  level: text("level").notNull(), // INFO, SUCCESS, ERROR, WARNING
  message: text("message").notNull(),
  timestamp: timestamp("timestamp").notNull().defaultNow(),
});

export const insertRfidTagSchema = createInsertSchema(rfidTags).pick({
  epc: true,
  rssi: true,
});

export const insertSystemLogSchema = createInsertSchema(systemLogs).pick({
  level: true,
  message: true,
});

export type InsertRfidTag = z.infer<typeof insertRfidTagSchema>;
export type RfidTag = typeof rfidTags.$inferSelect;
export type InsertSystemLog = z.infer<typeof insertSystemLogSchema>;
export type SystemLog = typeof systemLogs.$inferSelect;

// RFID Reader Types
export enum ReaderType {
  RRU9816 = 'RRU9816',
  IQRFID5102 = 'IQRFID-5102'
}

export interface ReaderConfig {
  type: ReaderType;
  port?: string;
  baudRate?: number;
  description: string;
  protocol: string;
  frequency: string;
}

// WebSocket message types
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

export interface WebSocketMessage {
  type: 'tag_read' | 'reader_status' | 'log_entry' | 'statistics';
  data: TagReadEvent | RfidReaderStatus | SystemLog | {
    totalReads: number;
    uniqueTags: number;
    readRate: number;
  };
}
