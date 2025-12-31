import { storage } from "../storage";
import type { User, Book } from "@shared/schema";

export interface IrbisUser {
  rfid: string;
  name: string;
  email?: string;
  phone?: string;
  blocked: boolean;
  reservations: string[];
}

export interface IrbisBook {
  rfid: string;
  title: string;
  author?: string;
  isbn?: string;
  available: boolean;
  reservedFor?: string;
}

export interface IrbisReservation {
  bookRfid: string;
  userRfid: string;
  reservedAt: string;
  expiresAt: string;
}

class IrbisService {
  private connected: boolean = false;
  private mockMode: boolean = true;

  async connect(): Promise<boolean> {
    if (this.mockMode) {
      this.connected = true;
      console.log('[IRBIS64] Mock mode: connected');
      return true;
    }
    return false;
  }

  async disconnect(): Promise<void> {
    this.connected = false;
    console.log('[IRBIS64] Disconnected');
  }

  isConnected(): boolean {
    return this.connected;
  }

  isMockMode(): boolean {
    return this.mockMode;
  }

  async getUser(rfid: string): Promise<IrbisUser | null> {
    if (this.mockMode) {
      const user = await storage.getUserByRfid(rfid);
      if (!user) return null;

      const reservedBooks = await storage.getReservedBooks(rfid);
      return {
        rfid: user.rfid,
        name: user.name,
        email: user.email ?? undefined,
        phone: user.phone ?? undefined,
        blocked: user.blocked ?? false,
        reservations: reservedBooks.map(b => b.rfid),
      };
    }
    return null;
  }

  async getBook(rfid: string): Promise<IrbisBook | null> {
    if (this.mockMode) {
      const book = await storage.getBookByRfid(rfid);
      if (!book) return null;

      return {
        rfid: book.rfid,
        title: book.title,
        author: book.author ?? undefined,
        isbn: book.isbn ?? undefined,
        available: book.status === 'available' || book.status === 'in_cabinet',
        reservedFor: book.reservedForRfid ?? undefined,
      };
    }
    return null;
  }

  async getReservations(userRfid: string): Promise<IrbisReservation[]> {
    if (this.mockMode) {
      const books = await storage.getReservedBooks(userRfid);
      return books.map(book => ({
        bookRfid: book.rfid,
        userRfid,
        reservedAt: new Date().toISOString(),
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      }));
    }
    return [];
  }

  async issueBook(bookRfid: string, userRfid: string): Promise<{ success: boolean; message: string }> {
    if (this.mockMode) {
      const book = await storage.getBookByRfid(bookRfid);
      const user = await storage.getUserByRfid(userRfid);

      if (!book) return { success: false, message: 'Книга не найдена' };
      if (!user) return { success: false, message: 'Пользователь не найден' };

      if (book.reservedForRfid && book.reservedForRfid !== userRfid) {
        return { success: false, message: 'Книга забронирована другим читателем' };
      }

      console.log(`[IRBIS64] Mock: Выдача книги ${book.title} пользователю ${user.name}`);
      return { success: true, message: 'Выдача зарегистрирована' };
    }
    return { success: false, message: 'ИРБИС не подключен' };
  }

  async returnBook(bookRfid: string, userRfid?: string): Promise<{ success: boolean; message: string }> {
    if (this.mockMode) {
      const book = await storage.getBookByRfid(bookRfid);
      if (!book) return { success: false, message: 'Книга не найдена' };

      console.log(`[IRBIS64] Mock: Возврат книги ${book.title}`);
      return { success: true, message: 'Возврат зарегистрирован' };
    }
    return { success: false, message: 'ИРБИС не подключен' };
  }

  async createReservation(bookRfid: string, userRfid: string): Promise<{ success: boolean; message: string }> {
    if (this.mockMode) {
      const book = await storage.getBookByRfid(bookRfid);
      const user = await storage.getUserByRfid(userRfid);

      if (!book) return { success: false, message: 'Книга не найдена' };
      if (!user) return { success: false, message: 'Пользователь не найден' };
      if (book.reservedForRfid) return { success: false, message: 'Книга уже забронирована' };

      console.log(`[IRBIS64] Mock: Бронирование книги ${book.title} для ${user.name}`);
      return { success: true, message: 'Бронирование создано' };
    }
    return { success: false, message: 'ИРБИС не подключен' };
  }

  async cancelReservation(bookRfid: string, userRfid: string): Promise<{ success: boolean; message: string }> {
    if (this.mockMode) {
      console.log(`[IRBIS64] Mock: Отмена бронирования ${bookRfid}`);
      return { success: true, message: 'Бронирование отменено' };
    }
    return { success: false, message: 'ИРБИС не подключен' };
  }
}

export const irbisService = new IrbisService();
