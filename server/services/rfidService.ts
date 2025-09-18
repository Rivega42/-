import { SerialPort } from 'serialport';
import { ReadlineParser } from '@serialport/parser-readline';
import EventEmitter from 'events';
import { storage } from '../storage';
import type { TagReadEvent, RfidReaderStatus, ReaderConfig } from '@shared/schema';
import { ReaderType } from '@shared/schema';

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

  constructor() {
    super();
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
    if (this.serialPort && this.serialPort.isOpen) {
      return new Promise((resolve) => {
        this.serialPort!.close(() => {
          this.serialPort = undefined;
          this.parser = undefined;
          resolve();
        });
      });
    }
  }

  private handleSerialData(data: string): void {
    try {
      // Parse RFID data - this is a simplified parser
      // Real RRU9816 protocol would need specific command/response handling
      const trimmed = data.trim();
      
      if (trimmed.length === 0) return;

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
    } catch (error) {
      console.error('Error parsing RFID data:', error);
      storage.addSystemLog({
        level: 'ERROR',
        message: `Error parsing RFID data: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
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
    // ACR1281U-C specific initialization commands
    // This NFC reader uses PC/SC CCID protocol, different from UHF readers
    // Initial setup command to put reader in polling mode for ISO14443 cards
    const setupCommand = Buffer.from([0x6F, 0x04, 0x00, 0x00, 0x00, 0x00]);
    this.serialPort?.write(setupCommand);
    
    storage.addSystemLog({
      level: 'INFO',
      message: 'Starting ACR1281U-C NFC card detection...',
    });
  }

  public manualInventory(): void {
    if (this.currentReaderType) {
      this.initializeReader(this.currentReaderType);
    }
  }

  public getConnectionStatus(): RfidReaderStatus {
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
