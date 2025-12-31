import { EventEmitter } from 'events';
import { storage } from '../storage';
import { irbisService } from './irbisService';
import type { Cell, Book, Operation } from '@shared/schema';

export type CellRow = 'FRONT' | 'BACK';

export interface CabinetPosition {
  x: number;
  y: number;
  row: CellRow;
}

export interface CabinetState {
  state: 'idle' | 'moving' | 'busy' | 'error' | 'maintenance';
  position: CabinetPosition;
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

export type CabinetEvent = 
  | 'state_changed'
  | 'cell_opened'
  | 'cell_closed'
  | 'book_detected'
  | 'book_removed'
  | 'operation_started'
  | 'operation_completed'
  | 'operation_failed'
  | 'tray_opened'
  | 'tray_closed';

class CabinetService extends EventEmitter {
  private state: CabinetState = {
    state: 'idle',
    position: { x: 0, y: 0, row: 'FRONT' },
    trayOpen: false,
    bookOnTray: null,
    sensors: {
      tray_sensor: false,
      book_sensor: false,
      door_closed: true,
      emergency_stop: false,
    },
    currentOperation: null,
    lastError: null,
  };

  private maintenanceMode: boolean = false;
  private operationTimeout: number = 30000;
  private moveDelay: number = 1500;
  private trayDelay: number = 800;

  getState(): CabinetState {
    return { ...this.state };
  }

  isMaintenanceMode(): boolean {
    return this.maintenanceMode;
  }

  async setMaintenanceMode(enabled: boolean): Promise<void> {
    this.maintenanceMode = enabled;
    if (enabled) {
      this.state.state = 'maintenance';
    } else {
      this.state.state = 'idle';
    }
    this.emit('state_changed', this.state);
    await storage.addLog('INFO', `Режим обслуживания: ${enabled ? 'включен' : 'выключен'}`);
  }

  private async delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private async moveToPosition(target: CabinetPosition): Promise<boolean> {
    if (this.maintenanceMode) {
      throw new Error('Шкаф в режиме обслуживания');
    }

    this.state.state = 'moving';
    this.emit('state_changed', this.state);

    const steps = Math.abs(target.x - this.state.position.x) + 
                  Math.abs(target.y - this.state.position.y) +
                  (target.row !== this.state.position.row ? 1 : 0);

    await this.delay(this.moveDelay * Math.max(1, steps / 3));

    this.state.position = { ...target };
    this.state.state = 'idle';
    this.emit('state_changed', this.state);

    return true;
  }

  private async openTray(): Promise<boolean> {
    if (this.state.trayOpen) return true;

    this.state.state = 'busy';
    this.emit('state_changed', this.state);

    await this.delay(this.trayDelay);

    this.state.trayOpen = true;
    this.state.sensors.tray_sensor = true;
    this.emit('tray_opened', this.state.position);
    this.emit('state_changed', this.state);

    return true;
  }

  private async closeTray(): Promise<boolean> {
    if (!this.state.trayOpen) return true;

    await this.delay(this.trayDelay);

    this.state.trayOpen = false;
    this.state.sensors.tray_sensor = false;
    this.state.state = 'idle';
    this.emit('tray_closed', this.state.position);
    this.emit('state_changed', this.state);

    return true;
  }

  async issueBook(bookRfid: string, userRfid: string): Promise<{
    success: boolean;
    message: string;
    operation?: Operation;
    cell?: Cell;
  }> {
    if (this.maintenanceMode) {
      return { success: false, message: 'Шкаф в режиме обслуживания' };
    }

    if (this.state.state !== 'idle') {
      return { success: false, message: 'Шкаф занят другой операцией' };
    }

    const book = await storage.getBookByRfid(bookRfid);
    if (!book) {
      return { success: false, message: 'Книга не найдена в системе' };
    }

    if (book.status !== 'in_cabinet' && book.status !== 'reserved') {
      return { success: false, message: `Книга недоступна для выдачи (статус: ${book.status})` };
    }

    if (book.reservedForRfid && book.reservedForRfid !== userRfid) {
      return { success: false, message: 'Книга забронирована другим читателем' };
    }

    if (book.cellId === null) {
      return { success: false, message: 'Книга не размещена в ячейке' };
    }

    const cell = await storage.getCellById(book.cellId);
    if (!cell) {
      return { success: false, message: 'Ячейка не найдена' };
    }

    this.state.state = 'busy';
    this.state.currentOperation = `Выдача: ${book.title}`;
    this.emit('operation_started', { type: 'issue', book, cell });
    this.emit('state_changed', this.state);

    try {
      await this.moveToPosition({ x: cell.x, y: cell.y, row: cell.row as CellRow });
      await this.openTray();

      this.state.sensors.book_sensor = true;
      this.state.bookOnTray = bookRfid;
      this.emit('book_detected', bookRfid);

      await irbisService.issueBook(bookRfid, userRfid);

      await storage.updateBook(book.id, {
        status: 'issued',
        issuedToRfid: userRfid,
        reservedForRfid: null,
        cellId: null,
      });

      await storage.updateCell(cell.id, {
        status: 'empty',
        bookRfid: null,
        bookTitle: null,
      });

      const operation = await storage.addOperation({
        operation: 'ISSUE',
        cellRow: cell.row,
        cellX: cell.x,
        cellY: cell.y,
        bookRfid,
        userRfid,
        result: 'OK',
      });

      await storage.addLog('SUCCESS', `Выдана книга "${book.title}" читателю ${userRfid}`);

      await this.delay(3000);

      this.state.sensors.book_sensor = false;
      this.state.bookOnTray = null;
      this.emit('book_removed', bookRfid);

      await this.closeTray();
      await this.moveToPosition({ x: 0, y: 0, row: 'FRONT' });

      this.state.currentOperation = null;
      this.state.state = 'idle';
      this.emit('operation_completed', { type: 'issue', operation });
      this.emit('state_changed', this.state);

      return { success: true, message: 'Книга выдана успешно', operation, cell };
    } catch (error: any) {
      this.state.state = 'error';
      this.state.lastError = error.message;
      this.state.currentOperation = null;

      const operation = await storage.addOperation({
        operation: 'ISSUE',
        cellRow: cell.row,
        cellX: cell.x,
        cellY: cell.y,
        bookRfid,
        userRfid,
        result: 'ERROR',
        errorMessage: error.message,
      });

      await storage.addLog('ERROR', `Ошибка выдачи книги "${book.title}": ${error.message}`);
      this.emit('operation_failed', { type: 'issue', error: error.message });
      this.emit('state_changed', this.state);

      return { success: false, message: error.message };
    }
  }

  async returnBook(bookRfid: string): Promise<{
    success: boolean;
    message: string;
    operation?: Operation;
    cell?: Cell;
  }> {
    if (this.maintenanceMode) {
      return { success: false, message: 'Шкаф в режиме обслуживания' };
    }

    if (this.state.state !== 'idle') {
      return { success: false, message: 'Шкаф занят другой операцией' };
    }

    const book = await storage.getBookByRfid(bookRfid);
    if (!book) {
      return { success: false, message: 'Книга не найдена в системе' };
    }

    if (book.status !== 'issued') {
      return { success: false, message: 'Книга не числится выданной' };
    }

    const emptyCell = await storage.getEmptyCell();
    if (!emptyCell) {
      return { success: false, message: 'Нет свободных ячеек для приёма книги' };
    }

    this.state.state = 'busy';
    this.state.currentOperation = `Возврат: ${book.title}`;
    this.emit('operation_started', { type: 'return', book, cell: emptyCell });
    this.emit('state_changed', this.state);

    try {
      this.state.sensors.book_sensor = true;
      this.state.bookOnTray = bookRfid;
      this.emit('book_detected', bookRfid);

      await irbisService.returnBook(bookRfid, book.issuedToRfid ?? undefined);

      await this.moveToPosition({ x: emptyCell.x, y: emptyCell.y, row: emptyCell.row as CellRow });
      await this.openTray();

      await storage.updateBook(book.id, {
        status: 'returned',
        issuedToRfid: null,
        cellId: emptyCell.id,
      });

      await storage.updateCell(emptyCell.id, {
        status: 'occupied',
        bookRfid,
        bookTitle: book.title,
        needsExtraction: true,
      });

      const operation = await storage.addOperation({
        operation: 'RETURN',
        cellRow: emptyCell.row,
        cellX: emptyCell.x,
        cellY: emptyCell.y,
        bookRfid,
        userRfid: book.issuedToRfid,
        result: 'OK',
      });

      await storage.addLog('SUCCESS', `Возвращена книга "${book.title}" в ячейку ${emptyCell.row} X${emptyCell.x} Y${emptyCell.y}`);

      await this.delay(2000);

      this.state.sensors.book_sensor = false;
      this.state.bookOnTray = null;

      await this.closeTray();
      await this.moveToPosition({ x: 0, y: 0, row: 'FRONT' });

      this.state.currentOperation = null;
      this.state.state = 'idle';
      this.emit('operation_completed', { type: 'return', operation });
      this.emit('state_changed', this.state);

      return { success: true, message: 'Книга возвращена успешно', operation, cell: emptyCell };
    } catch (error: any) {
      this.state.state = 'error';
      this.state.lastError = error.message;
      this.state.currentOperation = null;

      await storage.addLog('ERROR', `Ошибка возврата книги "${book.title}": ${error.message}`);
      this.emit('operation_failed', { type: 'return', error: error.message });
      this.emit('state_changed', this.state);

      return { success: false, message: error.message };
    }
  }

  async loadBook(bookRfid: string, title: string, author?: string): Promise<{
    success: boolean;
    message: string;
    cell?: Cell;
  }> {
    if (this.maintenanceMode) {
      return { success: false, message: 'Шкаф в режиме обслуживания' };
    }

    if (this.state.state !== 'idle') {
      return { success: false, message: 'Шкаф занят другой операцией' };
    }

    const existingBook = await storage.getBookByRfid(bookRfid);
    if (existingBook) {
      return { success: false, message: 'Книга с таким RFID уже существует' };
    }

    const emptyCell = await storage.getEmptyCell();
    if (!emptyCell) {
      return { success: false, message: 'Нет свободных ячеек' };
    }

    this.state.state = 'busy';
    this.state.currentOperation = `Загрузка: ${title}`;
    this.emit('state_changed', this.state);

    try {
      const book = await storage.addBook({
        rfid: bookRfid,
        title,
        author,
        status: 'in_cabinet',
        cellId: emptyCell.id,
      });

      await storage.updateCell(emptyCell.id, {
        status: 'occupied',
        bookRfid,
        bookTitle: title,
      });

      await this.moveToPosition({ x: emptyCell.x, y: emptyCell.y, row: emptyCell.row as CellRow });
      await this.openTray();
      await this.delay(2000);
      await this.closeTray();
      await this.moveToPosition({ x: 0, y: 0, row: 'FRONT' });

      await storage.addOperation({
        operation: 'LOAD',
        cellRow: emptyCell.row,
        cellX: emptyCell.x,
        cellY: emptyCell.y,
        bookRfid,
        result: 'OK',
      });

      await storage.addLog('SUCCESS', `Загружена книга "${title}" в ячейку ${emptyCell.row} X${emptyCell.x} Y${emptyCell.y}`);

      this.state.currentOperation = null;
      this.state.state = 'idle';
      this.emit('state_changed', this.state);

      return { success: true, message: 'Книга загружена успешно', cell: emptyCell };
    } catch (error: any) {
      this.state.state = 'error';
      this.state.lastError = error.message;
      this.state.currentOperation = null;
      this.emit('state_changed', this.state);

      return { success: false, message: error.message };
    }
  }

  async extractBook(cellId: number): Promise<{
    success: boolean;
    message: string;
    book?: Book;
  }> {
    if (this.state.state !== 'idle') {
      return { success: false, message: 'Шкаф занят другой операцией' };
    }

    const cell = await storage.getCellById(cellId);
    if (!cell) {
      return { success: false, message: 'Ячейка не найдена' };
    }

    if (!cell.bookRfid) {
      return { success: false, message: 'Ячейка пуста' };
    }

    const book = await storage.getBookByRfid(cell.bookRfid);
    if (!book) {
      return { success: false, message: 'Книга не найдена' };
    }

    this.state.state = 'busy';
    this.state.currentOperation = `Изъятие: ${book.title}`;
    this.emit('state_changed', this.state);

    try {
      await this.moveToPosition({ x: cell.x, y: cell.y, row: cell.row as CellRow });
      await this.openTray();

      await storage.updateBook(book.id, {
        status: 'available',
        cellId: null,
      });

      await storage.updateCell(cell.id, {
        status: 'empty',
        bookRfid: null,
        bookTitle: null,
        needsExtraction: false,
      });

      await storage.addOperation({
        operation: 'EXTRACT',
        cellRow: cell.row,
        cellX: cell.x,
        cellY: cell.y,
        bookRfid: book.rfid,
        result: 'OK',
      });

      await storage.addLog('SUCCESS', `Изъята книга "${book.title}" из ячейки ${cell.row} X${cell.x} Y${cell.y}`);

      await this.delay(3000);
      await this.closeTray();
      await this.moveToPosition({ x: 0, y: 0, row: 'FRONT' });

      this.state.currentOperation = null;
      this.state.state = 'idle';
      this.emit('state_changed', this.state);

      return { success: true, message: 'Книга изъята успешно', book };
    } catch (error: any) {
      this.state.state = 'error';
      this.state.lastError = error.message;
      this.state.currentOperation = null;
      this.emit('state_changed', this.state);

      return { success: false, message: error.message };
    }
  }

  async extractAllReturned(): Promise<{
    success: boolean;
    message: string;
    extracted: number;
  }> {
    const cellsToExtract = await storage.getCellsNeedingExtraction();
    let extracted = 0;

    for (const cell of cellsToExtract) {
      const result = await this.extractBook(cell.id);
      if (result.success) {
        extracted++;
      }
      await this.delay(500);
    }

    return {
      success: true,
      message: `Изъято ${extracted} из ${cellsToExtract.length} книг`,
      extracted,
    };
  }

  async reserveBook(bookRfid: string, userRfid: string): Promise<{
    success: boolean;
    message: string;
  }> {
    const book = await storage.getBookByRfid(bookRfid);
    if (!book) {
      return { success: false, message: 'Книга не найдена' };
    }

    if (book.status !== 'in_cabinet' && book.status !== 'available') {
      return { success: false, message: 'Книга недоступна для бронирования' };
    }

    if (book.reservedForRfid) {
      return { success: false, message: 'Книга уже забронирована' };
    }

    await storage.updateBook(book.id, {
      status: 'reserved',
      reservedForRfid: userRfid,
    });

    if (book.cellId) {
      await storage.updateCell(book.cellId, { status: 'reserved' });
    }

    await irbisService.createReservation(bookRfid, userRfid);
    await storage.addLog('INFO', `Книга "${book.title}" забронирована для ${userRfid}`);

    return { success: true, message: 'Книга забронирована' };
  }

  async cancelReservation(bookRfid: string, userRfid: string): Promise<{
    success: boolean;
    message: string;
  }> {
    const book = await storage.getBookByRfid(bookRfid);
    if (!book) {
      return { success: false, message: 'Книга не найдена' };
    }

    if (book.reservedForRfid !== userRfid) {
      return { success: false, message: 'Книга не забронирована этим пользователем' };
    }

    await storage.updateBook(book.id, {
      status: book.cellId ? 'in_cabinet' : 'available',
      reservedForRfid: null,
    });

    if (book.cellId) {
      await storage.updateCell(book.cellId, { status: 'occupied' });
    }

    await irbisService.cancelReservation(bookRfid, userRfid);
    await storage.addLog('INFO', `Бронирование книги "${book.title}" отменено`);

    return { success: true, message: 'Бронирование отменено' };
  }

  async runInventory(): Promise<{
    success: boolean;
    total: number;
    found: number;
    missing: number;
    details: Array<{ cell: Cell; status: 'ok' | 'missing' | 'unexpected' }>;
  }> {
    const cells = await storage.getAllCells();
    const details: Array<{ cell: Cell; status: 'ok' | 'missing' | 'unexpected' }> = [];
    let found = 0;
    let missing = 0;

    this.state.state = 'busy';
    this.state.currentOperation = 'Инвентаризация';
    this.emit('state_changed', this.state);

    for (const cell of cells) {
      if (cell.status === 'blocked') continue;

      await this.moveToPosition({ x: cell.x, y: cell.y, row: cell.row as CellRow });
      await this.delay(300);

      if (cell.bookRfid) {
        found++;
        details.push({ cell, status: 'ok' });
      } else if (cell.status === 'occupied') {
        missing++;
        details.push({ cell, status: 'missing' });
      }
    }

    await this.moveToPosition({ x: 0, y: 0, row: 'FRONT' });

    this.state.currentOperation = null;
    this.state.state = 'idle';
    this.emit('state_changed', this.state);

    await storage.addLog('INFO', `Инвентаризация завершена: ${found} книг найдено, ${missing} отсутствует`);

    return {
      success: true,
      total: cells.filter(c => c.status !== 'blocked').length,
      found,
      missing,
      details,
    };
  }

  clearError(): void {
    this.state.state = 'idle';
    this.state.lastError = null;
    this.emit('state_changed', this.state);
  }
}

export const cabinetService = new CabinetService();
