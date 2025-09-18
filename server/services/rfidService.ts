import { SerialPort } from 'serialport';
import { ReadlineParser } from '@serialport/parser-readline';
import EventEmitter from 'events';
import { storage } from '../storage';
import type { TagReadEvent, RfidReaderStatus, ReaderConfig } from '@shared/schema';
import { ReaderType } from '@shared/schema';
import { pcscService } from './pcscService';

// Reader configurations for different models
const READER_CONFIGS: Record<ReaderType, ReaderConfig> = {
  [ReaderType.RRU9816]: {
    type: ReaderType.RRU9816,
    baudRate: 57600,
    description: 'RRU9816 UHF RFID Reader',
    protocol: 'EPC C1G2 Protocol',
    frequency: '860-960MHz'
  },
  [ReaderType.IQRFID5102]: {
    type: ReaderType.IQRFID5102,
    baudRate: 115200,
    description: 'IQRFID-5102 Desktop UHF RFID Reader',
    protocol: 'EPC Class 1 Gen2 (ISO18000-6C)',
    frequency: 'UHF 860-960MHz'
  },
  [ReaderType.ACR1281UC]: {
    type: ReaderType.ACR1281UC,
    baudRate: 115200,
    description: 'ACR1281U-C DualBoost II USB NFC Reader',
    protocol: 'ISO 14443 Type A/B, ISO 7816-4',
    frequency: '13.56 MHz (NFC/HF)'
  }
};

export class RfidService extends EventEmitter {
  private serialPort?: SerialPort;
  private parser?: ReadlineParser;
  private isConnected = false;
  private currentPort?: string;
  private currentReaderType?: ReaderType;
  private isUsingPcsc = false;

  constructor() {
    super();
    this.setupPcscEventHandlers();
  }

  private setupPcscEventHandlers(): void {
    // Forward PC/SC service events to main service
    pcscService.on('tagRead', (tagEvent: TagReadEvent) => {
      this.emit('tagRead', tagEvent);
    });

    pcscService.on('status', (status: RfidReaderStatus) => {
      this.emit('status', status);
    });
  }

  async getAvailablePorts(): Promise<string[]> {
    try {
      const ports = await SerialPort.list();
      return ports
        .filter(port => port.path)
        .map(port => port.path)
        .sort();
    } catch (error) {
      console.error('Error listing ports:', error);
      return [];
    }
  }

  async connect(portPath: string, readerType: ReaderType, customBaudRate?: number): Promise<void> {
    if (this.isConnected) {
      await this.disconnect();
    }

    this.currentReaderType = readerType;

    // Route based on reader type: PC/SC for ACR1281U-C, Serial for UHF readers
    if (readerType === ReaderType.ACR1281UC) {
      return this.connectPcscReader();
    } else {
      return this.connectSerialReader(portPath, readerType, customBaudRate);
    }
  }

  private async connectPcscReader(): Promise<void> {
    try {
      this.isUsingPcsc = true;
      await pcscService.connect();
      
      this.isConnected = true;
      this.currentPort = 'PC/SC';

      storage.addSystemLog({
        level: 'INFO',
        message: 'ACR1281U-C connected via PC/SC protocol',
      });

      this.emit('status', {
        connected: true,
        readerType: ReaderType.ACR1281UC,
        port: 'PC/SC',
      } as RfidReaderStatus);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      storage.addSystemLog({
        level: 'ERROR',
        message: `Failed to connect via PC/SC: ${errorMessage}`,
      });
      
      this.emit('status', {
        connected: false,
        error: errorMessage,
      } as RfidReaderStatus);
      
      throw error;
    }
  }

  private async connectSerialReader(portPath: string, readerType: ReaderType, customBaudRate?: number): Promise<void> {
    const config = READER_CONFIGS[readerType];
    const baudRate = customBaudRate || config.baudRate || 57600;

    try {
      this.serialPort = new SerialPort({
        path: portPath,
        baudRate,
        dataBits: 8,
        parity: 'none',
        stopBits: 1,
      });

      this.parser = this.serialPort.pipe(new ReadlineParser({ delimiter: '\r\n' }));

      this.serialPort.on('open', () => {
        this.isConnected = true;
        this.currentPort = portPath;
        this.currentReaderType = readerType;
        this.emit('status', {
          connected: true,
          readerType,
          port: portPath,
        } as RfidReaderStatus);
        
        storage.addSystemLog({
          level: 'SUCCESS',
          message: `Connected to ${config.description} on port ${portPath}`,
        });

        // Initialize reader with type-specific commands
        this.initializeReader(readerType);
      });

      this.serialPort.on('error', (error) => {
        this.emit('status', {
          connected: false,
          error: error.message,
        } as RfidReaderStatus);
        
        storage.addSystemLog({
          level: 'ERROR',
          message: `Serial port error: ${error.message}`,
        });
      });

      this.serialPort.on('close', () => {
        this.isConnected = false;
        this.currentPort = undefined;
        this.currentReaderType = undefined;
        this.emit('status', {
          connected: false,
        } as RfidReaderStatus);
        
        storage.addSystemLog({
          level: 'INFO',
          message: 'Disconnected from RFID reader',
        });
      });

      if (this.parser) {
        this.parser.on('data', (data: string) => {
          this.handleSerialData(data);
        });
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.emit('status', {
        connected: false,
        error: errorMessage,
      } as RfidReaderStatus);
      
      storage.addSystemLog({
        level: 'ERROR',
        message: `Failed to connect to port ${portPath}: ${errorMessage}`,
      });
      
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    if (this.isUsingPcsc) {
      // Disconnect PC/SC reader
      await pcscService.disconnect();
      this.isUsingPcsc = false;
    } else if (this.serialPort && this.serialPort.isOpen) {
      // Disconnect serial reader
      return new Promise((resolve) => {
        this.serialPort!.close(() => {
          this.serialPort = undefined;
          this.parser = undefined;
          resolve();
        });
      });
    }

    this.isConnected = false;
    this.currentPort = undefined;
    this.currentReaderType = undefined;
  }

  private handleSerialData(data: string): void {
    try {
      // Parse RFID data based on reader type
      const trimmed = data.trim();
      
      if (trimmed.length === 0) return;

      // Parse based on reader type
      if (this.currentReaderType === ReaderType.ACR1281UC) {
        this.handleNfcData(trimmed);
      } else {
        this.handleUhfData(trimmed);
      }
    } catch (error) {
      console.error('Error parsing RFID data:', error);
      storage.addSystemLog({
        level: 'ERROR',
        message: `Error parsing RFID data: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  }

  private handleUhfData(trimmed: string): void {
    // Look for EPC patterns (typically 24 hex characters for EPC-96)
    const epcMatch = trimmed.match(/([0-9A-Fa-f\s]{24,})/);
    
    if (epcMatch) {
      const epc = epcMatch[1].replace(/\s+/g, ' ').toUpperCase();
      
      // Extract RSSI if present (look for dBm values)
      const rssiMatch = trimmed.match(/-?\d+\s*dBm/i);
      const rssi = rssiMatch ? parseFloat(rssiMatch[0].replace(/[^\d.-]/g, '')) : -50;

      const tagEvent: TagReadEvent = {
        epc,
        rssi,
        timestamp: new Date().toISOString(),
        readerType: this.currentReaderType,
      };

      // Store in database
      storage.createOrUpdateRfidTag({
        epc,
        rssi: rssi.toString(),
      });

      // Emit tag read event
      this.emit('tagRead', tagEvent);

      storage.addSystemLog({
        level: 'INFO',
        message: `Tag detected: ${epc}, RSSI: ${rssi} dBm`,
      });
    }
  }

  private handleNfcData(trimmed: string): void {
    // Look for NFC UID patterns (8, 14, or 20 hex characters)
    const nfcMatch = trimmed.match(/([0-9A-Fa-f\s]{8,20})\b/);
    
    if (nfcMatch) {
      const cleanUid = nfcMatch[1].replace(/\s+/g, '').toUpperCase();
      
      // Validate NFC UID length (4, 7, or 10 bytes)
      if (cleanUid.length === 8 || cleanUid.length === 14 || cleanUid.length === 20) {
        // NFC readers typically don't provide RSSI, use default
        const rssi = -30; // Default NFC signal strength
        
        // Format UID with spaces for display consistency
        const formattedUid = cleanUid.replace(/(.{2})/g, '$1 ').trim();

        const tagEvent: TagReadEvent = {
          epc: formattedUid,
          rssi,
          timestamp: new Date().toISOString(),
          readerType: this.currentReaderType,
        };

        // Store in database
        storage.createOrUpdateRfidTag({
          epc: formattedUid,
          rssi: rssi.toString(),
        });

        // Emit tag read event
        this.emit('tagRead', tagEvent);

        storage.addSystemLog({
          level: 'INFO',
          message: `NFC card detected: ${formattedUid}, Type: ISO14443`,
        });
      }
    }
  }

  private initializeReader(readerType: ReaderType): void {
    if (!this.serialPort || !this.serialPort.isOpen) return;

    try {
      switch (readerType) {
        case ReaderType.RRU9816:
          this.initializeRRU9816();
          break;
        case ReaderType.IQRFID5102:
          this.initializeIQRFID5102();
          break;
        case ReaderType.ACR1281UC:
          this.initializeACR1281UC();
          break;
        default:
          storage.addSystemLog({
            level: 'WARNING',
            message: `Unknown reader type: ${readerType}`,
          });
      }
    } catch (error) {
      storage.addSystemLog({
        level: 'ERROR',
        message: `Failed to initialize ${readerType}: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  }

  private initializeRRU9816(): void {
    // RRU9816 specific initialization commands
    const inventoryCommand = Buffer.from([0xA0, 0x03, 0x01, 0x89, 0x01, 0x8D]);
    this.serialPort?.write(inventoryCommand);
    
    storage.addSystemLog({
      level: 'INFO',
      message: 'Starting RRU9816 RFID inventory scan...',
    });
  }

  private initializeIQRFID5102(): void {
    // IQRFID-5102 specific initialization commands
    // This reader may use different command protocol
    const inventoryCommand = Buffer.from([0xBB, 0x00, 0x01, 0x00, 0x01, 0x7E]);
    this.serialPort?.write(inventoryCommand);
    
    storage.addSystemLog({
      level: 'INFO',
      message: 'Starting IQRFID-5102 RFID inventory scan...',
    });
  }

  private initializeACR1281UC(): void {
    // ACR1281U-C now uses dedicated PC/SC service
    // This method is kept for compatibility but delegates to PC/SC service
    storage.addSystemLog({
      level: 'INFO',
      message: 'ACR1281U-C initialization handled by PC/SC service',
    });
  }

  public manualInventory(): void {
    if (this.isUsingPcsc) {
      // PC/SC readers are always polling automatically
      storage.addSystemLog({
        level: 'INFO',
        message: 'Manual inventory requested for ACR1281U-C (always active)',
      });
    } else if (this.currentReaderType) {
      this.initializeReader(this.currentReaderType);
    }
  }

  public getConnectionStatus(): RfidReaderStatus {
    if (this.isUsingPcsc) {
      return pcscService.getConnectionStatus();
    }
    
    return {
      connected: this.isConnected,
      readerType: this.currentReaderType,
      port: this.currentPort,
    };
  }

  public getReaderConfigs(): Record<ReaderType, ReaderConfig> {
    return READER_CONFIGS;
  }

  public getReaderConfig(readerType: ReaderType): ReaderConfig {
    return READER_CONFIGS[readerType];
  }
}

export const rfidService = new RfidService();
