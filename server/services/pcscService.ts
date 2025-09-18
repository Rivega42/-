import { EventEmitter } from 'events';
import type { TagReadEvent, RfidReaderStatus } from '@shared/schema';
import { ReaderType } from '@shared/schema';
import { storage } from '../storage';

// Interface for PC/SC functionality
interface PcscReader {
  name: string;
  connect(options: any, callback: (err: Error | null, protocol?: number) => void): void;
  transmit(command: Buffer, maxLength: number, callback: (err: Error | null, response?: Buffer) => void): void;
  disconnect(callback: (err: Error | null) => void): void;
  on(event: string, listener: (...args: any[]) => void): void;
}

interface NfcPcsc {
  on(event: string, listener: (...args: any[]) => void): void;
}

// APDU Commands for different card types
const APDU_COMMANDS = {
  // Get UID for ISO14443 Type A cards (like MIFARE)
  GET_UID_TYPE_A: Buffer.from([0xFF, 0xCA, 0x00, 0x00, 0x00]),
  
  // Select application for ISO14443 Type B cards
  SELECT_APP_TYPE_B: Buffer.from([0x00, 0xA4, 0x04, 0x00, 0x0E, 0x32, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31]),
  
  // ISO7816 Get Data command for UID
  GET_DATA: Buffer.from([0x00, 0xCA, 0x01, 0x00, 0x08])
};

export class PcscService extends EventEmitter {
  private nfc: NfcPcsc | null = null;
  private isAvailable = false;
  private isConnected = false;
  private currentReader: PcscReader | null = null;
  private pollingInterval: NodeJS.Timeout | null = null;
  private initPromise: Promise<void>;
  
  constructor() {
    super();
    this.initPromise = this.checkPcscAvailability();
  }

  private async checkPcscAvailability(): Promise<void> {
    try {
      // Try to dynamically import nfc-pcsc (optional dependency)
      const nfcModule = await import('nfc-pcsc').catch(() => null);
      if (!nfcModule) throw new Error('nfc-pcsc module not available');
      
      const { NFC } = nfcModule;
      this.nfc = new NFC();
      this.isAvailable = true;
      this.setupNfcEventHandlers();
      
      storage.addSystemLog({
        level: 'INFO',
        message: 'PC/SC service initialized successfully - real hardware support enabled',
      });
    } catch (error) {
      this.isAvailable = false;
      storage.addSystemLog({
        level: 'INFO',
        message: 'PC/SC not available - using simulation mode for ACR1281U-C',
      });
    }
  }

  private setupNfcEventHandlers(): void {
    if (!this.nfc) return;

    this.nfc.on('reader', (reader: PcscReader) => {
      storage.addSystemLog({
        level: 'INFO',
        message: `PC/SC reader detected: ${reader.name}`,
      });

      // Check if this is ACR1281U-C NFC reader (PICC interface only)
      if (reader.name.toLowerCase().includes('acr1281') && 
          reader.name.toLowerCase().includes('picc')) {
        this.currentReader = reader;
        storage.addSystemLog({
          level: 'INFO',
          message: `Selected NFC reader: ${reader.name}`,
        });
        this.setupReaderEventHandlers(reader);
      }
    });

    this.nfc.on('error', (error: Error) => {
      storage.addSystemLog({
        level: 'ERROR',
        message: `PC/SC error: ${error.message}`,
      });
      this.emit('status', {
        connected: false,
        error: error.message,
      } as RfidReaderStatus);
    });
  }

  private setupReaderEventHandlers(reader: PcscReader): void {
    reader.on('card', (card: any) => {
      storage.addSystemLog({
        level: 'INFO',
        message: 'NFC card detected on ACR1281U-C',
      });
      this.processAutoCard(card);
    });

    reader.on('card.off', () => {
      storage.addSystemLog({
        level: 'INFO',
        message: 'NFC card removed from ACR1281U-C',
      });
    });

    reader.on('error', (error: Error) => {
      storage.addSystemLog({
        level: 'WARNING',
        message: `Reader error (will retry): ${error.message}`,
      });
      // Не прерываем работу - это могут быть временные ошибки
    });
  }

  private processAutoCard(card: any): void {
    storage.addSystemLog({
      level: 'INFO',
      message: `Processing card automatically connected by nfc-pcsc`,
    });

    try {
      // nfc-pcsc библиотека автоматически подключается и предоставляет card объект
      let uid = '';
      
      if (card && card.uid) {
        // Получаем UID напрямую из card объекта
        uid = Array.from(card.uid).map((b: number) => b.toString(16).padStart(2, '0').toUpperCase()).join(' ');
        
        storage.addSystemLog({
          level: 'INFO',
          message: `Card UID extracted: ${uid}`,
        });
        
        this.processNfcCard(uid);
      } else {
        storage.addSystemLog({
          level: 'WARNING',
          message: `Card object missing UID data: ${JSON.stringify(card)}`,
        });
      }
    } catch (error) {
      storage.addSystemLog({
        level: 'ERROR',
        message: `Error processing auto-connected card: ${error instanceof Error ? error.message : String(error)}`,
      });
    }
  }

  private processNfcCard(uid: string): void {
    if (!uid || uid.trim() === '') {
      storage.addSystemLog({
        level: 'WARNING',
        message: 'Empty or invalid UID received',
      });
      return;
    }

    // Format UID with spaces for consistency
    const formattedUid = uid.trim();

    const tagEvent: TagReadEvent = {
      epc: formattedUid,
      rssi: -25, // PC/SC doesn't provide RSSI, use strong signal indication
      timestamp: new Date().toISOString(),
      readerType: ReaderType.ACR1281UC,
    };

    // Store in database
    storage.createOrUpdateRfidTag({
      epc: formattedUid,
      rssi: '-25',
    });

    // Emit tag read event
    this.emit('tagRead', tagEvent);

    storage.addSystemLog({
      level: 'INFO',
      message: `✅ Real NFC card read: ${formattedUid}`,
    });
  }

  async connect(): Promise<void> {
    // Wait for initialization to complete
    await this.initPromise;
    
    if (!this.isAvailable) {
      // Fallback to simulation mode
      this.startSimulation();
      return;
    }

    // Wait for actual reader detection (with timeout)
    const readerTimeout = new Promise<void>((_, reject) => {
      setTimeout(() => reject(new Error('No ACR1281U-C reader found within 5 seconds')), 5000);
    });

    const readerFound = new Promise<void>((resolve) => {
      if (this.currentReader) {
        resolve();
        return;
      }
      
      const onReader = (reader: PcscReader) => {
        if (reader.name.toLowerCase().includes('acr1281') && 
            reader.name.toLowerCase().includes('picc')) {
          this.currentReader = reader;
          storage.addSystemLog({
            level: 'INFO',
            message: `Selected NFC reader for connection: ${reader.name}`,
          });
          try {
            this.nfc?.removeListener?.('reader', onReader);
          } catch (e) {
            // Ignore listener removal errors
          }
          resolve();
        }
      };
      
      this.nfc?.on('reader', onReader);
    });

    try {
      await Promise.race([readerFound, readerTimeout]);
      
      this.isConnected = true;
      this.emit('status', {
        connected: true,
        readerType: ReaderType.ACR1281UC,
        port: 'PC/SC',
      } as RfidReaderStatus);

      storage.addSystemLog({
        level: 'INFO',
        message: 'Connected to ACR1281U-C via PC/SC protocol',
      });
      
    } catch (error) {
      // Fallback to simulation if no hardware found
      storage.addSystemLog({
        level: 'WARNING',
        message: 'ACR1281U-C hardware not found, using simulation mode',
      });
      this.startSimulation();
    }
  }

  async disconnect(): Promise<void> {
    this.isConnected = false;
    
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }

    if (this.currentReader) {
      this.currentReader.disconnect(() => {
        storage.addSystemLog({
          level: 'INFO',
          message: 'Disconnected from ACR1281U-C',
        });
      });
      this.currentReader = null;
    }

    this.emit('status', {
      connected: false,
    } as RfidReaderStatus);
  }

  private startSimulation(): void {
    // Simulation mode for environments without PC/SC support
    this.isConnected = true;
    this.emit('status', {
      connected: true,
      readerType: ReaderType.ACR1281UC,
      port: 'SIMULATION',
    } as RfidReaderStatus);

    storage.addSystemLog({
      level: 'INFO',
      message: 'ACR1281U-C simulation mode started (PC/SC not available)',
    });

    // Start polling simulation
    this.pollingInterval = setInterval(() => {
      this.simulateNfcDetection();
    }, 8000 + Math.random() * 4000); // 8-12 seconds
  }

  private simulateNfcDetection(): void {
    if (!this.isConnected) return;

    const sampleNfcUids = [
      '04 A1 2B 34',      // 4-byte UID
      '04 A1 2B 34 56 C7',  // 7-byte UID 
      '04 A1 2B 34 56 C7 89 12'  // 10-byte UID
    ];
    
    const randomUid = sampleNfcUids[Math.floor(Math.random() * sampleNfcUids.length)];
    
    const tagEvent: TagReadEvent = {
      epc: randomUid,
      rssi: -28,
      timestamp: new Date().toISOString(),
      readerType: ReaderType.ACR1281UC,
    };

    storage.createOrUpdateRfidTag({
      epc: randomUid,
      rssi: '-28',
    });

    this.emit('tagRead', tagEvent);
    
    storage.addSystemLog({
      level: 'INFO',
      message: `Simulated NFC detection: ${randomUid}`,
    });
  }

  public getConnectionStatus(): RfidReaderStatus {
    return {
      connected: this.isConnected,
      readerType: ReaderType.ACR1281UC,
      port: this.isAvailable ? 'PC/SC' : 'SIMULATION',
    };
  }

  public isReady(): boolean {
    return this.isAvailable || true; // Always ready (simulation fallback)
  }

  public getAvailableReaders(): string[] {
    // In real PC/SC environment, this would enumerate readers
    return this.isAvailable ? ['ACR1281U-C'] : ['ACR1281U-C (Simulation)'];
  }
}

export const pcscService = new PcscService();