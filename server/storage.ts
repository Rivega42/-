import { 
  type RfidTag, type InsertRfidTag, 
  type SystemLog, type InsertSystemLog,
  type Cell, type InsertCell,
  type User, type InsertUser,
  type Book, type InsertBook,
  type Operation, type InsertOperation,
  type Setting, type InsertSetting,
  type Statistics, type SystemStatus,
  BLOCKED_CELLS
} from "@shared/schema";
import { randomUUID } from "crypto";

export interface IStorage {
  // Cells
  getCell(id: number): Promise<Cell | undefined>;
  getCellById(id: number): Promise<Cell | undefined>;
  getCellByPosition(row: string, x: number, y: number): Promise<Cell | undefined>;
  getAllCells(): Promise<Cell[]>;
  updateCell(id: number, data: Partial<Cell>): Promise<Cell | undefined>;
  getAvailableCells(row?: string): Promise<Cell[]>;
  getCellsNeedingExtraction(): Promise<Cell[]>;
  getEmptyCell(): Promise<Cell | undefined>;

  // Users
  getUser(id: string): Promise<User | undefined>;
  getUserByRfid(rfid: string): Promise<User | undefined>;
  getAllUsers(): Promise<User[]>;
  createUser(user: InsertUser): Promise<User>;
  updateUser(id: string, data: Partial<User>): Promise<User | undefined>;

  // Books
  getBook(id: string): Promise<Book | undefined>;
  getBookByRfid(rfid: string): Promise<Book | undefined>;
  getAllBooks(): Promise<Book[]>;
  createBook(book: InsertBook): Promise<Book>;
  addBook(book: InsertBook): Promise<Book>;
  updateBook(id: string, data: Partial<Book>): Promise<Book | undefined>;
  getReservedBooks(userRfid: string): Promise<Book[]>;
  getBooksInCabinet(): Promise<Book[]>;

  // Operations
  getOperation(id: string): Promise<Operation | undefined>;
  getAllOperations(limit?: number): Promise<Operation[]>;
  createOperation(op: InsertOperation): Promise<Operation>;
  addOperation(op: InsertOperation): Promise<Operation>;
  getOperationsToday(): Promise<Operation[]>;

  // Settings
  getSetting(key: string): Promise<Setting | undefined>;
  getAllSettings(): Promise<Setting[]>;
  setSetting(key: string, value: string, description?: string): Promise<Setting>;

  // RFID Tags
  getRfidTag(epc: string): Promise<RfidTag | undefined>;
  getAllRfidTags(): Promise<RfidTag[]>;
  createOrUpdateRfidTag(tag: InsertRfidTag): Promise<RfidTag>;
  clearAllRfidTags(): Promise<void>;
  
  // System Logs
  addSystemLog(log: InsertSystemLog): Promise<SystemLog>;
  addLog(level: string, message: string, component?: string): Promise<SystemLog>;
  getAllSystemLogs(limit?: number): Promise<SystemLog[]>;
  clearSystemLogs(): Promise<void>;
  
  // Statistics
  getStatistics(): Promise<Statistics>;
}

export class MemStorage implements IStorage {
  private cells: Map<number, Cell>;
  private users: Map<string, User>;
  private books: Map<string, Book>;
  private operations: Map<string, Operation>;
  private settings: Map<string, Setting>;
  private rfidTags: Map<string, RfidTag>;
  private systemLogs: Map<string, SystemLog>;
  private readHistory: Date[];

  constructor() {
    this.cells = new Map();
    this.users = new Map();
    this.books = new Map();
    this.operations = new Map();
    this.settings = new Map();
    this.rfidTags = new Map();
    this.systemLogs = new Map();
    this.readHistory = [];
    
    this.initializeCells();
    this.initializeMockData();
  }

  private initializeCells(): void {
    let cellId = 0;
    const rows: ('FRONT' | 'BACK')[] = ['FRONT', 'BACK'];
    
    for (const row of rows) {
      for (let x = 0; x < 3; x++) {
        for (let y = 0; y < 21; y++) {
          const isBlocked = BLOCKED_CELLS[row].some(
            cell => cell.x === x && cell.y === y
          );
          
          this.cells.set(cellId, {
            id: cellId,
            row,
            x,
            y,
            status: isBlocked ? 'blocked' : 'empty',
            bookRfid: null,
            bookTitle: null,
            reservedFor: null,
            needsExtraction: false,
            updatedAt: new Date(),
          });
          cellId++;
        }
      }
    }
  }

  private initializeMockData(): void {
    const mockUsers: InsertUser[] = [
      { rfid: 'CARD001', name: 'Иванов Иван Иванович', role: 'reader', email: 'ivanov@mail.ru' },
      { rfid: 'CARD002', name: 'Петрова Мария Сергеевна', role: 'reader', email: 'petrova@mail.ru' },
      { rfid: 'ADMIN01', name: 'Козлова Анна Викторовна', role: 'librarian', email: 'kozlova@library.ru' },
      { rfid: 'ADMIN99', name: 'Администратор', role: 'admin', email: 'admin@library.ru' },
    ];
    mockUsers.forEach(u => this.createUserSync(u));

    const mockBooks: InsertBook[] = [
      { rfid: 'BOOK001', title: 'Война и мир', author: 'Л.Н. Толстой', isbn: '978-5-17-000001-1', status: 'reserved', reservedForRfid: 'CARD001' },
      { rfid: 'BOOK002', title: 'Мастер и Маргарита', author: 'М.А. Булгаков', isbn: '978-5-17-000002-2', status: 'in_cabinet' },
      { rfid: 'BOOK003', title: '1984', author: 'Дж. Оруэлл', isbn: '978-5-17-000003-3', status: 'reserved', reservedForRfid: 'CARD002' },
      { rfid: 'BOOK004', title: 'Преступление и наказание', author: 'Ф.М. Достоевский', isbn: '978-5-17-000004-4', status: 'in_cabinet' },
      { rfid: 'BOOK005', title: 'Анна Каренина', author: 'Л.Н. Толстой', isbn: '978-5-17-000005-5', status: 'in_cabinet' },
    ];
    mockBooks.forEach(b => this.createBookSync(b));

    this.placeBookInCell('BOOK001', 0, 'FRONT', 0, 0, 'CARD001');
    this.placeBookInCell('BOOK002', 1, 'FRONT', 0, 1);
    this.placeBookInCell('BOOK003', 2, 'FRONT', 0, 2, 'CARD002');
    this.placeBookInCell('BOOK004', 3, 'FRONT', 2, 0);
    this.placeBookInCell('BOOK005', 4, 'BACK', 0, 0);

    this.addSystemLogSync({ level: 'INFO', message: 'Система инициализирована с тестовыми данными', component: 'SYSTEM' });
  }

  private createUserSync(user: InsertUser): User {
    const newUser: User = {
      id: randomUUID(),
      rfid: user.rfid,
      name: user.name,
      role: user.role ?? 'reader',
      email: user.email ?? null,
      phone: user.phone ?? null,
      blocked: user.blocked ?? false,
      createdAt: new Date(),
    };
    this.users.set(newUser.id, newUser);
    return newUser;
  }

  private createBookSync(book: InsertBook): Book {
    const newBook: Book = {
      id: randomUUID(),
      rfid: book.rfid,
      title: book.title,
      author: book.author ?? null,
      isbn: book.isbn ?? null,
      status: book.status ?? 'available',
      reservedForRfid: book.reservedForRfid ?? null,
      issuedToRfid: book.issuedToRfid ?? null,
      cellId: book.cellId ?? null,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    this.books.set(newBook.id, newBook);
    return newBook;
  }

  private placeBookInCell(bookRfid: string, cellId: number, row: string, x: number, y: number, reservedFor?: string): void {
    const cell = this.cells.get(cellId);
    const book = Array.from(this.books.values()).find(b => b.rfid === bookRfid);
    
    if (cell && book) {
      cell.status = reservedFor ? 'reserved' : 'occupied';
      cell.bookRfid = bookRfid;
      cell.bookTitle = book.title;
      cell.reservedFor = reservedFor ?? null;
      cell.updatedAt = new Date();
      
      book.cellId = cellId;
      book.updatedAt = new Date();
    }
  }

  private addSystemLogSync(log: InsertSystemLog): SystemLog {
    const newLog: SystemLog = {
      id: randomUUID(),
      level: log.level,
      message: log.message,
      component: log.component ?? null,
      timestamp: new Date(),
    };
    this.systemLogs.set(newLog.id, newLog);
    return newLog;
  }

  // === CELLS ===
  async getCell(id: number): Promise<Cell | undefined> {
    return this.cells.get(id);
  }

  async getCellByPosition(row: string, x: number, y: number): Promise<Cell | undefined> {
    return Array.from(this.cells.values()).find(
      c => c.row === row && c.x === x && c.y === y
    );
  }

  async getAllCells(): Promise<Cell[]> {
    return Array.from(this.cells.values()).sort((a, b) => a.id - b.id);
  }

  async updateCell(id: number, data: Partial<Cell>): Promise<Cell | undefined> {
    const cell = this.cells.get(id);
    if (!cell) return undefined;
    
    const updated = { ...cell, ...data, updatedAt: new Date() };
    this.cells.set(id, updated);
    return updated;
  }

  async getAvailableCells(row?: string): Promise<Cell[]> {
    return Array.from(this.cells.values()).filter(
      c => c.status === 'empty' && (!row || c.row === row)
    );
  }

  async getCellsNeedingExtraction(): Promise<Cell[]> {
    return Array.from(this.cells.values()).filter(c => c.needsExtraction);
  }

  async getCellById(id: number): Promise<Cell | undefined> {
    return this.cells.get(id);
  }

  async getEmptyCell(): Promise<Cell | undefined> {
    return Array.from(this.cells.values()).find(c => c.status === 'empty');
  }

  // === USERS ===
  async getUser(id: string): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByRfid(rfid: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(u => u.rfid === rfid);
  }

  async getAllUsers(): Promise<User[]> {
    return Array.from(this.users.values());
  }

  async createUser(user: InsertUser): Promise<User> {
    return this.createUserSync(user);
  }

  async updateUser(id: string, data: Partial<User>): Promise<User | undefined> {
    const user = this.users.get(id);
    if (!user) return undefined;
    
    const updated = { ...user, ...data };
    this.users.set(id, updated);
    return updated;
  }

  // === BOOKS ===
  async getBook(id: string): Promise<Book | undefined> {
    return this.books.get(id);
  }

  async getBookByRfid(rfid: string): Promise<Book | undefined> {
    return Array.from(this.books.values()).find(b => b.rfid === rfid);
  }

  async getAllBooks(): Promise<Book[]> {
    return Array.from(this.books.values());
  }

  async createBook(book: InsertBook): Promise<Book> {
    return this.createBookSync(book);
  }

  async addBook(book: InsertBook): Promise<Book> {
    return this.createBookSync(book);
  }

  async updateBook(id: string, data: Partial<Book>): Promise<Book | undefined> {
    const book = this.books.get(id);
    if (!book) return undefined;
    
    const updated = { ...book, ...data, updatedAt: new Date() };
    this.books.set(id, updated);
    return updated;
  }

  async getReservedBooks(userRfid: string): Promise<Book[]> {
    return Array.from(this.books.values()).filter(
      b => b.reservedForRfid === userRfid && b.status === 'reserved'
    );
  }

  async getBooksInCabinet(): Promise<Book[]> {
    return Array.from(this.books.values()).filter(
      b => b.status === 'in_cabinet' || b.status === 'reserved'
    );
  }

  // === OPERATIONS ===
  async getOperation(id: string): Promise<Operation | undefined> {
    return this.operations.get(id);
  }

  async getAllOperations(limit?: number): Promise<Operation[]> {
    const ops = Array.from(this.operations.values()).sort(
      (a, b) => new Date(b.timestamp!).getTime() - new Date(a.timestamp!).getTime()
    );
    return limit ? ops.slice(0, limit) : ops;
  }

  async createOperation(op: InsertOperation): Promise<Operation> {
    const newOp: Operation = {
      id: randomUUID(),
      timestamp: new Date(),
      operation: op.operation,
      cellRow: op.cellRow ?? null,
      cellX: op.cellX ?? null,
      cellY: op.cellY ?? null,
      bookRfid: op.bookRfid ?? null,
      userRfid: op.userRfid ?? null,
      result: op.result ?? 'OK',
      errorMessage: op.errorMessage ?? null,
      durationMs: op.durationMs ?? null,
    };
    this.operations.set(newOp.id, newOp);
    return newOp;
  }

  async addOperation(op: InsertOperation): Promise<Operation> {
    return this.createOperation(op);
  }

  async getOperationsToday(): Promise<Operation[]> {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    return Array.from(this.operations.values()).filter(
      op => op.timestamp && new Date(op.timestamp) >= today
    );
  }

  // === SETTINGS ===
  async getSetting(key: string): Promise<Setting | undefined> {
    return this.settings.get(key);
  }

  async getAllSettings(): Promise<Setting[]> {
    return Array.from(this.settings.values());
  }

  async setSetting(key: string, value: string, description?: string): Promise<Setting> {
    const setting: Setting = {
      key,
      value,
      description: description ?? null,
      updatedAt: new Date(),
    };
    this.settings.set(key, setting);
    return setting;
  }

  // === RFID TAGS ===
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
    
    this.readHistory.push(now);
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

  // === SYSTEM LOGS ===
  async addSystemLog(log: InsertSystemLog): Promise<SystemLog> {
    return this.addSystemLogSync(log);
  }

  async addLog(level: string, message: string, component?: string): Promise<SystemLog> {
    return this.addSystemLogSync({ level, message, component });
  }

  async getAllSystemLogs(limit?: number): Promise<SystemLog[]> {
    const logs = Array.from(this.systemLogs.values()).sort((a, b) => 
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
    return limit ? logs.slice(0, limit) : logs;
  }

  async clearSystemLogs(): Promise<void> {
    this.systemLogs.clear();
  }

  // === STATISTICS ===
  async getStatistics(): Promise<Statistics> {
    const totalReads = Array.from(this.rfidTags.values()).reduce((sum, tag) => sum + tag.readCount, 0);
    const uniqueTags = this.rfidTags.size;
    
    const now = new Date();
    const oneMinuteAgo = new Date(now.getTime() - 60 * 1000);
    const recentReads = this.readHistory.filter(time => time > oneMinuteAgo);
    const readRate = recentReads.length / 60;

    const allOps = await this.getAllOperations();
    const todayOps = await this.getOperationsToday();

    const issuesTotal = allOps.filter(op => op.operation === 'ISSUE').length;
    const issuesToday = todayOps.filter(op => op.operation === 'ISSUE').length;
    const returnsTotal = allOps.filter(op => op.operation === 'RETURN').length;
    const returnsToday = todayOps.filter(op => op.operation === 'RETURN').length;

    const allCells = await this.getAllCells();
    const totalCells = allCells.filter(c => c.status !== 'blocked').length;
    const occupiedCells = allCells.filter(c => c.status === 'occupied' || c.status === 'reserved').length;
    const booksNeedExtraction = allCells.filter(c => c.needsExtraction).length;

    return {
      totalReads,
      uniqueTags,
      readRate: Math.round(readRate * 10) / 10,
      issuesTotal,
      issuesToday,
      returnsTotal,
      returnsToday,
      occupiedCells,
      totalCells,
      booksNeedExtraction,
    };
  }
}

export const storage = new MemStorage();
