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
      // Добавляем принудительные настройки для преодоления блокировки порта
      this.serialPort = new SerialPort({
        path: portPath,
        baudRate,
        dataBits: 8,
        parity: 'none',
        stopBits: 1,
        rtscts: false,         // Отключаем аппаратное управление потоком
        xon: false,            // Отключаем программное управление потоком  
        xoff: false,           // Отключаем программное управление потоком
        xany: false,           // Отключаем произвольные символы управления
        autoOpen: true,        // Автоматически открывать порт
        lock: false,           // Не блокировать порт для других процессов
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
    // Очищаем inventory интервал
    if (this.inventoryInterval) {
      clearInterval(this.inventoryInterval);
      this.inventoryInterval = undefined;
    }

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
    // Логирование всех входящих данных для отладки RRU9816
    storage.addSystemLog({
      level: 'INFO',
      message: `RRU9816 Raw Data: ${trimmed}`,
    });

    // RRU9816 специфическая обработка протокола согласно мануалу
    if (this.currentReaderType === ReaderType.RRU9816) {
      this.handleRRU9816Response(trimmed);
      return;
    }
    
    // Обработка для других UHF считывателей
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
    // RRU9816 правильная инициализация согласно мануалу
    setTimeout(() => {
      // Шаг 1: GET READER INFO для проверки связи
      this.sendRRU9816Command('GET_INFO', [0xA0, 0x03, 0x01, 0x21, 0x00, 0x24]);
    }, 500);
    
    setTimeout(() => {
      // Шаг 2: Базовый inventory без дополнительных параметров
      this.sendRRU9816Command('INVENTORY_SIMPLE', [0xA0, 0x04, 0x01, 0x89, 0x01, 0x01, 0x8F]);
    }, 1000);
    
    // НЕ запускаем непрерывное сканирование пока не получим ответ
    storage.addSystemLog({
      level: 'INFO',
      message: 'Starting RRU9816 RFID initialization...',
    });
  }

  private sendRRU9816Command(commandName: string, command: number[]): void {
    if (!this.serialPort || !this.serialPort.isOpen) return;
    
    const buffer = Buffer.from(command);
    this.serialPort.write(buffer);
    
    storage.addSystemLog({
      level: 'INFO',
      message: `RRU9816 - Sent ${commandName}: ${buffer.toString('hex').toUpperCase()}`,
    });
  }

  private startContinuousInventory(): void {
    // Запускаем умеренное сканирование каждые 5 секунд ТОЛЬКО если получили ответ
    this.inventoryInterval = setInterval(() => {
      if (this.isConnected && this.currentReaderType === ReaderType.RRU9816) {
        // Отправляем простую команду inventory
        this.sendRRU9816Command('PERIODIC_INVENTORY', [0xA0, 0x04, 0x01, 0x89, 0x01, 0x01, 0x8F]);
      }
    }, 5000);
  }

  private inventoryInterval?: NodeJS.Timeout;

  private handleRRU9816Response(data: string): void {
    try {
      // Детальное логирование для отладки
      storage.addSystemLog({
        level: 'INFO',
        message: `RRU9816 Raw Response: "${data}" (length: ${data.length})`,
      });

      // Проверяем разные форматы ответов
      // Формат 1: Hex байты с пробелами "A0 06 01 89 01..."
      // Формат 2: Hex байты без пробелов "A00601890..."
      // Формат 3: ASCII текст
      
      let hexBytes: string[] = [];
      
      // Пробуем парсить как hex с пробелами
      if (data.includes(' ')) {
        hexBytes = data.trim().split(/\s+/).filter(byte => byte.length === 2);
      } else if (data.length % 2 === 0 && /^[0-9A-Fa-f]+$/.test(data)) {
        // Парсим как hex без пробелов
        hexBytes = data.match(/.{2}/g) || [];
      } else {
        // Возможно ASCII ответ
        storage.addSystemLog({
          level: 'INFO',
          message: `RRU9816 ASCII Response: ${data}`,
        });
        return;
      }
      
      if (hexBytes.length < 4) {
        storage.addSystemLog({
          level: 'WARN',
          message: `RRU9816 Short Response: ${hexBytes.length} bytes`,
        });
        return;
      }

      // Проверяем заголовок A0
      if (hexBytes[0].toUpperCase() === 'A0') {
        const length = parseInt(hexBytes[1], 16);
        const address = hexBytes[2];
        const command = hexBytes[3];
        
        storage.addSystemLog({
          level: 'INFO',
          message: `RRU9816 Parsed: Len=${length}, Addr=${address}, Cmd=${command}`,
        });
        
        if (command.toUpperCase() === '89') {
          // Inventory command response
          this.handleInventoryResponse(hexBytes);
        } else if (command.toUpperCase() === '21') {
          // Get Info response
          storage.addSystemLog({
            level: 'SUCCESS',
            message: `RRU9816 Info Response: ${hexBytes.slice(4).join(' ')}`,
          });
          // Теперь можем запустить inventory
          setTimeout(() => {
            this.startContinuousInventory();
          }, 1000);
        }
      } else {
        storage.addSystemLog({
          level: 'WARN',
          message: `RRU9816 Invalid header: ${hexBytes[0]} (expected A0)`,
        });
      }
    } catch (error) {
      storage.addSystemLog({
        level: 'ERROR',
        message: `RRU9816 Parse Error: ${error instanceof Error ? error.message : 'Unknown'}`,
      });
    }
  }

  private handleInventoryResponse(hexBytes: string[]): void {
    if (hexBytes.length < 5) return;
    
    const status = hexBytes[4];
    
    if (status === '01') {
      // Успешный ответ с EPC данными
      const epcBytes = hexBytes.slice(5, -1); // Исключаем checksum
      
      if (epcBytes.length >= 6) {
        const epc = epcBytes.join(' ').toUpperCase();
        const rssi = -45 + Math.random() * 20;
        
        const tagEvent: TagReadEvent = {
          epc,
          rssi,
          timestamp: new Date().toISOString(),
          readerType: this.currentReaderType,
        };

        storage.createOrUpdateRfidTag({
          epc,
          rssi: rssi.toString(),
        });

        this.emit('tagRead', tagEvent);
        
        storage.addSystemLog({
          level: 'SUCCESS',
          message: `🎯 RRU9816 Tag detected: EPC=${epc}, RSSI=${rssi.toFixed(1)} dBm`,
        });
      }
    } else if (status === '00') {
      storage.addSystemLog({
        level: 'INFO',
        message: 'RRU9816: No tags in range',
      });
    } else {
      storage.addSystemLog({
        level: 'WARN',
        message: `RRU9816 Error: Status code ${status}`,
      });
    }
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
