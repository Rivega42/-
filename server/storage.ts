import { type RfidTag, type InsertRfidTag, type SystemLog, type InsertSystemLog } from "@shared/schema";
import { randomUUID } from "crypto";

export interface IStorage {
  // RFID Tags
  getRfidTag(epc: string): Promise<RfidTag | undefined>;
  getAllRfidTags(): Promise<RfidTag[]>;
  createOrUpdateRfidTag(tag: InsertRfidTag): Promise<RfidTag>;
  clearAllRfidTags(): Promise<void>;
  
  // System Logs
  addSystemLog(log: InsertSystemLog): Promise<SystemLog>;
  getAllSystemLogs(): Promise<SystemLog[]>;
  clearSystemLogs(): Promise<void>;
  
  // Statistics
  getStatistics(): Promise<{
    totalReads: number;
    uniqueTags: number;
    readRate: number;
  }>;
}

export class MemStorage implements IStorage {
  private rfidTags: Map<string, RfidTag>;
  private systemLogs: Map<string, SystemLog>;
  private readHistory: Date[];

  constructor() {
    this.rfidTags = new Map();
    this.systemLogs = new Map();
    this.readHistory = [];
  }

  async getRfidTag(epc: string): Promise<RfidTag | undefined> {
    return this.rfidTags.get(epc);
  }

  async getAllRfidTags(): Promise<RfidTag[]> {
    return Array.from(this.rfidTags.values()).sort((a, b) => 
      new Date(b.lastSeen).getTime() - new Date(a.lastSeen).getTime()
    );
  }

  async createOrUpdateRfidTag(insertTag: InsertRfidTag): Promise<RfidTag> {
    const existing = this.rfidTags.get(insertTag.epc);
    const now = new Date();
    
    // Track read for statistics
    this.readHistory.push(now);
    // Keep only last 5 minutes of history for rate calculation
    const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
    this.readHistory = this.readHistory.filter(time => time > fiveMinutesAgo);

    if (existing) {
      const updated: RfidTag = {
        ...existing,
        rssi: insertTag.rssi ?? null,
        readCount: existing.readCount + 1,
        lastSeen: now,
      };
      this.rfidTags.set(insertTag.epc, updated);
      return updated;
    } else {
      const newTag: RfidTag = {
        id: randomUUID(),
        epc: insertTag.epc,
        rssi: insertTag.rssi ?? null,
        readCount: 1,
        firstSeen: now,
        lastSeen: now,
      };
      this.rfidTags.set(insertTag.epc, newTag);
      return newTag;
    }
  }

  async clearAllRfidTags(): Promise<void> {
    this.rfidTags.clear();
    this.readHistory = [];
  }

  async addSystemLog(insertLog: InsertSystemLog): Promise<SystemLog> {
    const log: SystemLog = {
      id: randomUUID(),
      level: insertLog.level,
      message: insertLog.message,
      timestamp: new Date(),
    };
    this.systemLogs.set(log.id, log);
    return log;
  }

  async getAllSystemLogs(): Promise<SystemLog[]> {
    return Array.from(this.systemLogs.values()).sort((a, b) => 
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }

  async clearSystemLogs(): Promise<void> {
    this.systemLogs.clear();
  }

  async getStatistics(): Promise<{
    totalReads: number;
    uniqueTags: number;
    readRate: number;
  }> {
    const totalReads = Array.from(this.rfidTags.values()).reduce((sum, tag) => sum + tag.readCount, 0);
    const uniqueTags = this.rfidTags.size;
    
    // Calculate read rate (reads per second) based on last 5 minutes
    const now = new Date();
    const oneMinuteAgo = new Date(now.getTime() - 60 * 1000);
    const recentReads = this.readHistory.filter(time => time > oneMinuteAgo);
    const readRate = recentReads.length / 60; // reads per second

    return {
      totalReads,
      uniqueTags,
      readRate: Math.round(readRate * 10) / 10, // round to 1 decimal
    };
  }
}

export const storage = new MemStorage();
