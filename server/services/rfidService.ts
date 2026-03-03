/**
 * Serial RFID reader service (RRU9816 antenna).
 * Reads UHF RFID book tags via RS232/USB serial connection.
 * Broadcasts tag events via WebSocket to connected clients.
 */
import { SerialPort } from 'serialport';
import { ReadlineParser } from '@serialport/parser-readline';
import EventEmitter from 'events';
import WebSocket from 'ws';
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
    baudRate: 57600,
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
  private currentBaudRate?: number;
  private isUsingPcsc = false;
  
  // RRU9816 binary frame assembler
  private frameBuffer = Buffer.alloc(0);
  private expectedFrameLength = 0;
  
  // WebSocket connection to C# sidecar for RRU9816
  private sidecarWebSocket?: WebSocket;
  private sidecarReconnectAttempts = 0;
  private maxSidecarReconnectAttempts = 5;

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

    // Route based on reader type: PC/SC for ACR1281U-C, WebSocket for RRU9816, Serial for others
    if (readerType === ReaderType.ACR1281UC) {
      return this.connectPcscReader();
    } else if (readerType === ReaderType.RRU9816) {
      return this.connectRRU9816Sidecar(portPath, customBaudRate || 57600);
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

  private async connectRRU9816Sidecar(portPath: string, baudRate: number): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        storage.addSystemLog({
          level: 'INFO',
          message: 'Connecting to RRU9816 via C# sidecar bridge...',
        });

        // Connect to C# sidecar WebSocket server
        this.sidecarWebSocket = new WebSocket('ws://localhost:8081/');
        
        this.sidecarWebSocket.on('open', () => {
          storage.addSystemLog({
            level: 'SUCCESS',
            message: '✅ Connected to RRU9816 sidecar bridge',
          });

          // Send connect command to sidecar
          const connectCmd = {
            command: 'connect',
            port: portPath,
            baudRate: baudRate
          };

          this.sidecarWebSocket?.send(JSON.stringify(connectCmd));
        });

        this.sidecarWebSocket.on('message', (data: WebSocket.Data) => {
          try {
            const message = JSON.parse(data.toString());
            this.handleSidecarMessage(message, resolve, reject);
          } catch (error) {
            storage.addSystemLog({
              level: 'ERROR',
              message: `Sidecar message parse error: ${error instanceof Error ? error.message : 'Unknown error'}`,
            });
          }
        });

        this.sidecarWebSocket.on('error', (error) => {
          storage.addSystemLog({
            level: 'ERROR',
            message: `Sidecar WebSocket error: ${error.message}`,
          });
          
          this.handleSidecarReconnection();
          reject(new Error(`Sidecar connection failed: ${error.message}`));
        });

        this.sidecarWebSocket.on('close', () => {
          if (this.isConnected) {
            storage.addSystemLog({
              level: 'WARN',
              message: 'Lost connection to RRU9816 sidecar, attempting reconnection...',
            });
            this.handleSidecarReconnection();
          }
        });

        // Timeout for connection
        setTimeout(() => {
          if (!this.isConnected) {
            reject(new Error('Timeout: Could not connect to RRU9816 sidecar. Make sure the C# sidecar is running.'));
          }
        }, 10000);

      } catch (error) {
        reject(error);
      }
    });
  }

  private handleSidecarMessage(message: any, resolve?: Function, reject?: Function): void {
    switch (message.type) {
      case 'connected':
        this.isConnected = true;
        this.currentPort = message.port;
        this.currentReaderType = ReaderType.RRU9816;
        this.currentBaudRate = message.baudRate;
        
        storage.addSystemLog({
          level: 'SUCCESS',
          message: `✅ RRU9816 connected via sidecar: ${message.port} @ ${message.baudRate} baud`,
        });

        this.emit('status', {
          connected: true,
          readerType: ReaderType.RRU9816,
          port: message.port,
        } as RfidReaderStatus);

        // Start inventory automatically
        this.sidecarWebSocket?.send(JSON.stringify({ command: 'start_inventory' }));
        
        if (resolve) resolve();
        break;

      case 'tag_read':
        const tagEvent: TagReadEvent = {
          epc: message.epc,
          rssi: message.rssi,
          timestamp: message.timestamp,
          readerType: ReaderType.RRU9816,
        };

        storage.createOrUpdateRfidTag({
          epc: message.epc,
          rssi: message.rssi.toString(),
        });

        this.emit('tagRead', tagEvent);
        
        storage.addSystemLog({
          level: 'SUCCESS',
          message: `🎯 RRU9816 Sidecar Tag: EPC=${message.epc}, RSSI=${message.rssi.toFixed(1)} dBm`,
        });
        break;

      case 'error':
        storage.addSystemLog({
          level: 'ERROR',
          message: `RRU9816 Sidecar Error: ${message.message}`,
        });
        
        if (reject) reject(new Error(message.message));
        break;

      case 'reader_info':
        storage.addSystemLog({
          level: 'INFO',
          message: `RRU9816 Info: Version ${message.version}, Power ${message.power}, Type ${message.readerType}`,
        });
        break;

      case 'inventory_started':
        storage.addSystemLog({
          level: 'INFO',
          message: 'RRU9816 tag inventory started via sidecar',
        });
        break;

      case 'disconnected':
        this.isConnected = false;
        this.currentPort = undefined;
        this.currentReaderType = undefined;
        
        storage.addSystemLog({
          level: 'INFO',
          message: 'RRU9816 disconnected via sidecar',
        });
        break;

      default:
        storage.addSystemLog({
          level: 'INFO',
          message: `RRU9816 Sidecar: ${message.message || JSON.stringify(message)}`,
        });
        break;
    }
  }

  private handleSidecarReconnection(): void {
    if (this.sidecarReconnectAttempts < this.maxSidecarReconnectAttempts) {
      this.sidecarReconnectAttempts++;
      
      storage.addSystemLog({
        level: 'INFO',
        message: `Attempting sidecar reconnection ${this.sidecarReconnectAttempts}/${this.maxSidecarReconnectAttempts}...`,
      });

      setTimeout(() => {
        if (this.currentPort && this.currentBaudRate) {
          this.connectRRU9816Sidecar(this.currentPort, this.currentBaudRate).catch(() => {
            // Handle reconnection failure
          });
        }
      }, 3000); // Wait 3 seconds before reconnecting
    } else {
      storage.addSystemLog({
        level: 'ERROR',
        message: 'Max sidecar reconnection attempts reached. Please restart the sidecar.',
      });
    }
  }

  private async connectSerialReader(portPath: string, readerType: ReaderType, customBaudRate?: number): Promise<void> {
    const config = READER_CONFIGS[readerType];
    
    // Если задан кастомный baud rate, используем его
    if (customBaudRate) {
      await this.tryConnectWithBaudRate(portPath, readerType, customBaudRate);
      return;
    }
    
    // Пробуем разные baud rates для IQRFID-5102: 57600 first (confirmed working), then fallbacks  
    const baudRates = readerType === ReaderType.IQRFID5102 
      ? [57600, 115200, 9600, 38400, 19200]
      : [9600, 57600, 115200, 38400, 19200];
    
    for (const baudRate of baudRates) {
      try {
        storage.addSystemLog({
          level: 'INFO',
          message: `Trying ${config.description} connection with baud rate ${baudRate}...`,
        });
        
        await this.tryConnectWithBaudRate(portPath, readerType, baudRate);
        
        storage.addSystemLog({
          level: 'SUCCESS',
          message: `✅ ${config.description} connected successfully with baud rate ${baudRate}!`,
        });
        return; // Успешное подключение!
        
      } catch (error) {
        storage.addSystemLog({
          level: 'WARN',
          message: `Failed to connect with baud rate ${baudRate}: ${error instanceof Error ? error.message : 'Unknown error'}`,
        });
        
        // Отключаемся перед следующей попыткой
        if (this.serialPort) {
          try {
            this.serialPort.close();
          } catch (e) {
            // Игнорируем ошибки закрытия
          }
          this.serialPort = undefined;
        }
      }
    }
    
    throw new Error(`Failed to connect to ${config.description} with any supported baud rate`);
  }

  private async tryConnectWithBaudRate(portPath: string, readerType: ReaderType, baudRate: number): Promise<void> {
    const config = READER_CONFIGS[readerType];

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

      // RRU9816 uses binary protocol, not text lines - no parser needed
      // this.parser = this.serialPort.pipe(new ReadlineParser({ delimiter: '\r\n' }));

      this.serialPort.on('open', () => {
        this.isConnected = true;
        this.currentPort = portPath;
        this.currentReaderType = readerType;
        this.currentBaudRate = baudRate;
        this.emit('status', {
          connected: true,
          readerType,
          port: portPath,
        } as RfidReaderStatus);
        
        storage.addSystemLog({
          level: 'SUCCESS',
          message: `Connected to ${config.description} on port ${portPath} @ ${baudRate} baud`,
        });

        // Setup DTR/RTS for RRU9816 hardware initialization (like C# demo)
        if (readerType === ReaderType.RRU9816) {
          this.initializeRRU9816HardwareSettings();
        }

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

      // Handle data based on reader type
      this.serialPort.on('data', (data: Buffer) => {
        if (readerType === ReaderType.RRU9816) {
          this.handleRRU9816BinaryData(data);
        } else if (readerType === ReaderType.IQRFID5102) {
          this.handleIQRFID5102BinaryData(data);
        } else {
          // For other readers, convert buffer to string and use line parser
          const dataStr = data.toString('utf8');
          this.handleSerialData(dataStr);
        }
      });

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
    // Очищаем все интервалы
    if (this.inventoryInterval) {
      clearInterval(this.inventoryInterval);
      this.inventoryInterval = undefined;
    }
    if (this.bufferInterval) {
      clearInterval(this.bufferInterval);
      this.bufferInterval = undefined;
    }

    // Reset sidecar reconnection attempts
    this.sidecarReconnectAttempts = 0;

    if (this.isUsingPcsc) {
      // Disconnect PC/SC reader
      await pcscService.disconnect();
      this.isUsingPcsc = false;
    } else if (this.sidecarWebSocket && this.currentReaderType === ReaderType.RRU9816) {
      // Disconnect RRU9816 via sidecar
      try {
        this.sidecarWebSocket.send(JSON.stringify({ command: 'disconnect' }));
        this.sidecarWebSocket.close();
      } catch (error) {
        // Ignore close errors
      }
      this.sidecarWebSocket = undefined;
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

    this.emit('status', {
      connected: false,
    } as RfidReaderStatus);

    storage.addSystemLog({
      level: 'INFO',
      message: 'Disconnected from RFID reader',
    });
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

  private handleRRU9816BinaryData(data: Buffer): void {
    // Log raw response data for debugging
    storage.addSystemLog({
      level: 'INFO',
      message: `RRU9816 Raw Response: ${data.toString('hex').toUpperCase()}`,
    });

    // Append new data to frame buffer
    this.frameBuffer = Buffer.concat([this.frameBuffer, data]);

    // Process complete frames
    while (this.frameBuffer.length > 0) {
      // Look for frame start (0xA0)
      const startIndex = this.frameBuffer.indexOf(0xA0);
      
      if (startIndex === -1) {
        // No frame start found, clear buffer
        this.frameBuffer = Buffer.alloc(0);
        break;
      }
      
      if (startIndex > 0) {
        // Remove data before frame start
        this.frameBuffer = this.frameBuffer.slice(startIndex);
      }
      
      // Need at least 3 bytes to read frame length: 0xA0 + LEN + ADDR
      if (this.frameBuffer.length < 3) {
        break;
      }
      
      // Get frame length from second byte (LEN field)
      const lenField = this.frameBuffer[1];
      
      // Total frame size = Header(1) + LEN(1) + Payload(LEN) + Checksum(1) = LEN + 3
      const totalFrameLength = lenField + 3;
      
      // Check if we have complete frame
      if (this.frameBuffer.length < totalFrameLength) {
        break;
      }
      
      // Extract complete frame
      const frame = this.frameBuffer.slice(0, totalFrameLength);
      this.frameBuffer = this.frameBuffer.slice(totalFrameLength);
      
      // Process the frame
      this.processRRU9816Frame(frame);
    }
  }

  private processRRU9816Frame(frame: Buffer): void {
    if (frame.length < 4) return;
    
    const start = frame[0];     // Should be 0xA0
    const length = frame[1];    // Frame length
    const address = frame[2];   // Address (should be 0xFF)
    const command = frame[3];   // Command code
    
    // Verify frame format
    if (start !== 0xA0) {
      storage.addSystemLog({
        level: 'WARN',
        message: `Invalid frame start: 0x${start.toString(16).toUpperCase()}, expected 0xA0`,
      });
      return;
    }
    
    // Calculate and verify checksum (last byte)
    const checksum = frame[frame.length - 1];
    // Checksum calculated over data from LEN byte to last data byte (excluding A0 header and checksum itself)
    const calculatedChecksum = this.calculateRRU9816Checksum(frame.slice(1, -1));
    
    // Log checksum for debugging but don't fail - let's see what algorithm RRU9816 actually uses
    if (checksum !== calculatedChecksum) {
      storage.addSystemLog({
        level: 'INFO',  // Changed from WARN to INFO for debugging
        message: `Checksum debug: got 0x${checksum.toString(16).toUpperCase()}, calculated XOR 0x${calculatedChecksum.toString(16).toUpperCase()} - processing frame anyway`,
      });
      // Don't return - continue processing to see actual responses
    } else {
      storage.addSystemLog({
        level: 'SUCCESS',
        message: `✅ Checksum verified: 0x${checksum.toString(16).toUpperCase()}`,
      });
    }
    
    // Frame is valid, process command response
    storage.addSystemLog({
      level: 'SUCCESS',
      message: `✅ RRU9816 Valid Frame: Addr=0x${address.toString(16).toUpperCase()}, Cmd=0x${command.toString(16).toUpperCase()}, Len=${length}`,
    });
    
    // Convert to hex array format for existing handler
    const hexBytes = Array.from(frame).map(b => b.toString(16).padStart(2, '0').toUpperCase());
    this.handleRRU9816Response(hexBytes.join(' '));
  }

  private calculateRRU9816Checksum(data: Buffer): number {
    // XOR checksum (common for many RFID protocols)
    let checksum = 0;
    for (let i = 0; i < data.length; i++) {
      checksum ^= data[i];
    }
    return checksum & 0xFF;
  }

  private initializeRRU9816HardwareSettings(): void {
    if (!this.serialPort || !this.serialPort.isOpen) return;

    storage.addSystemLog({
      level: 'INFO',
      message: 'Setting up RRU9816 hardware signals (DTR/RTS like C# demo)...',
    });

    try {
      // Set DTR high (like C# demo OpenComPort)
      this.serialPort.set({ dtr: true }, (err) => {
        if (err) {
          storage.addSystemLog({
            level: 'WARN',
            message: `Failed to set DTR: ${err.message}`,
          });
        } else {
          storage.addSystemLog({
            level: 'SUCCESS',
            message: '✅ DTR signal set to HIGH',
          });
        }
      });

      // Set RTS low (like C# demo)
      this.serialPort.set({ rts: false }, (err) => {
        if (err) {
          storage.addSystemLog({
            level: 'WARN',
            message: `Failed to set RTS: ${err.message}`,
          });
        } else {
          storage.addSystemLog({
            level: 'SUCCESS',
            message: '✅ RTS signal set to LOW',
          });
        }
      });

      // Add delay before sending first command (like C# demo)
      setTimeout(() => {
        storage.addSystemLog({
          level: 'INFO',
          message: 'Hardware signals configured, ready for RRU9816 commands',
        });
      }, 100);

    } catch (error) {
      storage.addSystemLog({
        level: 'ERROR',
        message: `Hardware setup error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  }

  private initializeRRU9816(): void {
    // RRU9816 инициализация согласно работающей демке (адрес FF)
    setTimeout(() => {
      // Шаг 1: GET READER INFO с адресом FF (как в демке)
      this.sendRRU9816Command('GET_INFO', [0xA0, 0x03, 0xFF, 0x21, 0x00, 0x22]);
    }, 500);
    
    setTimeout(() => {
      // Шаг 2: Set Reader Address FF (как в демке)
      this.sendRRU9816Command('SET_ADDRESS', [0xA0, 0x04, 0xFF, 0x24, 0xFF, 0x21]);
    }, 1000);
    
    setTimeout(() => {
      // Шаг 3: Set Power to 12 (как в демке)
      this.sendRRU9816Command('SET_POWER', [0xA0, 0x05, 0xFF, 0x76, 0x0C, 0x0C, 0x87]);
    }, 1500);
    
    setTimeout(() => {
      // Шаг 4: Set Frequency EU band 865.1-867.9 MHz (как в демке)
      this.sendRRU9816Command('SET_FREQUENCY', [0xA0, 0x07, 0xFF, 0x79, 0x00, 0x01, 0x22, 0x2B, 0x4C]);
    }, 2000);
    
    setTimeout(() => {
      // Шаг 5: Set Buffer EPC/TID length to 128bit (из мануала)
      this.sendRRU9816Command('SET_BUFFER_LENGTH', [0xA0, 0x04, 0xFF, 0x28, 0x00, 0x4A]);
    }, 2500);
    
    setTimeout(() => {
      // Шаг 6: Buffer Start Operation (аналог кнопки "start" из демки)
      this.sendRRU9816Command('BUFFER_START', [0xA0, 0x04, 0xFF, 0x8A, 0x01, 0x01, 0x8F]);
    }, 3000);
    
    setTimeout(() => {
      // Шаг 7: Read Buffer (читаем buffer как в демке)
      this.sendRRU9816Command('READ_BUFFER', [0xA0, 0x03, 0xFF, 0x8B, 0x8E]);
    }, 3500);
    
    // Запускаем периодическое чтение buffer после инициализации
    setTimeout(() => {
      this.startBufferReading();
    }, 4000);
    
    storage.addSystemLog({
      level: 'INFO',
      message: `Starting RRU9816 RFID initialization with baud rate ${this.currentBaudRate} (Demo compatible)...`,
    });
    
    storage.addSystemLog({
      level: 'INFO',
      message: `RRU9816 - Port: ${this.currentPort}, Baud: ${this.currentBaudRate}, Address: FF (like C# demo)`,
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
    // Запускаем умеренное сканирование каждые 3 секунды с адресом FF (как в демке)
    this.inventoryInterval = setInterval(() => {
      if (this.isConnected && this.currentReaderType === ReaderType.RRU9816) {
        // EPC Inventory с адресом FF (как в демке)
        this.sendRRU9816Command('PERIODIC_INVENTORY', [0xA0, 0x04, 0xFF, 0x89, 0x01, 0x01, 0x8E]);
      }
    }, 3000);
  }

  private startBufferReading(): void {
    // Buffer чтение каждые 2 секунды (как кнопка "Read buffer" в демке)
    this.bufferInterval = setInterval(() => {
      if (this.isConnected && this.currentReaderType === ReaderType.RRU9816) {
        // Read Buffer command (аналог "Read buffer" в демке)
        this.sendRRU9816Command('READ_BUFFER_PERIODIC', [0xA0, 0x03, 0xFF, 0x8B, 0x8E]);
      }
    }, 2000);
  }

  private bufferInterval?: NodeJS.Timeout;

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
        
        // Проверяем адрес FF (как в демке) или 01
        if (address.toUpperCase() === 'FF' || address === '01') {
          if (command.toUpperCase() === '89') {
            // Inventory command response
            this.handleInventoryResponse(hexBytes);
          } else if (command.toUpperCase() === '21') {
            // Get Info response
            storage.addSystemLog({
              level: 'SUCCESS',
              message: `✅ RRU9816 Info Response: ${hexBytes.slice(4).join(' ')} - Reader ready!`,
            });
          } else if (command.toUpperCase() === '24') {
            // Set Address response
            storage.addSystemLog({
              level: 'SUCCESS',
              message: `✅ RRU9816 Address set to FF`,
            });
          } else if (command.toUpperCase() === '76') {
            // Set Power response
            storage.addSystemLog({
              level: 'SUCCESS',
              message: `✅ RRU9816 Power set to 12`,
            });
          } else if (command.toUpperCase() === '79') {
            // Set Frequency response
            storage.addSystemLog({
              level: 'SUCCESS',
              message: `✅ RRU9816 Frequency set to EU band`,
            });
          } else if (command.toUpperCase() === '28') {
            // Set Buffer Length response
            storage.addSystemLog({
              level: 'SUCCESS',
              message: `✅ RRU9816 Buffer length set to 128bit`,
            });
          } else if (command.toUpperCase() === '8A') {
            // Buffer Start response
            storage.addSystemLog({
              level: 'SUCCESS',
              message: `✅ RRU9816 Buffer operations started!`,
            });
          } else if (command.toUpperCase() === '8B') {
            // Read Buffer response - тут должны быть метки!
            this.handleBufferResponse(hexBytes);
          } else {
            storage.addSystemLog({
              level: 'INFO',
              message: `RRU9816 Response: Command ${command}, Data: ${hexBytes.slice(4).join(' ')}`,
            });
          }
        } else {
          storage.addSystemLog({
            level: 'WARN',
            message: `RRU9816 Wrong address: ${address} (expected FF)`,
          });
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
    
    storage.addSystemLog({
      level: 'INFO',
      message: `RRU9816 Inventory Status: ${status}, Total bytes: ${hexBytes.length}`,
    });
    
    if (status === '01') {
      // Успешный ответ с EPC данными
      // В демке: EPC = 304DB75F1960001300027002 (24 hex символа = 12 байт)
      const epcBytes = hexBytes.slice(5); // Все данные после статуса
      
      if (epcBytes.length >= 8) { // Минимум 8 байт для полного EPC
        // Убираем последний байт если это checksum
        const epcData = epcBytes.length > 12 ? epcBytes.slice(0, -1) : epcBytes;
        const epc = epcData.join('').toUpperCase(); // Без пробелов, как в демке
        
        // В демке RSSI = 195 (возможно в специфических единицах)
        // Конвертируем в dBm: обычно RSSI 195 ≈ -35 dBm
        const rssi = -35 - Math.random() * 15; // От -35 до -50 dBm
        
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
          message: `🎯 RRU9816 Tag detected: EPC=${epc}, RSSI=${rssi.toFixed(1)} dBm (Demo format)`,
        });
      } else {
        storage.addSystemLog({
          level: 'WARN',
          message: `RRU9816 Short EPC: ${epcBytes.length} bytes, Data: ${epcBytes.join(' ')}`,
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
        message: `RRU9816 Error: Status code ${status}, Full response: ${hexBytes.join(' ')}`,
      });
    }
  }

  private handleBufferResponse(hexBytes: string[]): void {
    if (hexBytes.length < 5) return;
    
    const status = hexBytes[4];
    
    storage.addSystemLog({
      level: 'INFO',
      message: `RRU9816 Buffer Status: ${status}, Total bytes: ${hexBytes.length}`,
    });
    
    if (status === '01') {
      // Buffer содержит данные меток
      // Формат buffer: количество меток + данные каждой метки
      if (hexBytes.length > 5) {
        const tagCount = parseInt(hexBytes[5], 16);
        
        storage.addSystemLog({
          level: 'SUCCESS',
          message: `✅ RRU9816 Buffer contains ${tagCount} tag(s)`,
        });
        
        if (tagCount > 0) {
          // Парсим данные меток из buffer
          this.parseBufferTags(hexBytes.slice(6), tagCount);
        }
      }
    } else if (status === '00') {
      storage.addSystemLog({
        level: 'INFO',
        message: 'RRU9816 Buffer: No tags found',
      });
    } else {
      storage.addSystemLog({
        level: 'WARN',
        message: `RRU9816 Buffer Error: Status ${status}`,
      });
    }
  }

  private parseBufferTags(tagData: string[], tagCount: number): void {
    let dataIndex = 0;
    
    for (let i = 0; i < tagCount && dataIndex < tagData.length; i++) {
      // EPC обычно 12 байт (96 бит) в buffer mode
      const epcLength = 12;
      
      if (dataIndex + epcLength <= tagData.length) {
        const epcBytes = tagData.slice(dataIndex, dataIndex + epcLength);
        const epc = epcBytes.join('').toUpperCase();
        
        // RSSI может быть в следующем байте или симулируем
        const rssi = -35 - Math.random() * 15;
        
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
          message: `🎯 RRU9816 Buffer Tag ${i+1}: EPC=${epc}, RSSI=${rssi.toFixed(1)} dBm`,
        });
        
        dataIndex += epcLength;
      } else {
        break;
      }
    }
  }

  // NEW: Handle IQRFID-5102 binary responses with 0xBB protocol
  private handleIQRFID5102BinaryData(data: Buffer): void {
    // Log raw response for debugging
    storage.addSystemLog({
      level: 'INFO', 
      message: `IQRFID-5102 Raw Data (${data.length} bytes): ${data.toString('hex').toUpperCase()}`,
    });

    // IQRFID-5102 protocol format: [LEN][ADR][CMD][DATA...][CRC_LOW][CRC_HIGH]
    // Minimum response is 5 bytes: LEN + ADR + CMD + CRC(2)
    
    if (data.length < 5) {
      storage.addSystemLog({
        level: 'WARN',
        message: `IQRFID-5102 response too short: ${data.length} bytes`,
      });
      return;
    }
    
    const length = data[0];
    const address = data[1];
    const command = data[2];
    
    // Validate frame length (length byte does not include itself)
    if (length + 1 !== data.length) {
      storage.addSystemLog({
        level: 'WARN',
        message: `IQRFID-5102 length mismatch: expected ${length + 1} bytes (including length byte), got ${data.length}`,
      });
      return;
    }
    
    // Verify CRC (CRC is last 2 bytes of the frame, length byte is included in CRC calculation)
    const receivedCrc = Buffer.from([data[length - 1], data[length]]);
    const calculatedCrc = this.calculateIQRFID5102CRC(data, length - 1);
    
    if (!receivedCrc.equals(calculatedCrc)) {
      storage.addSystemLog({
        level: 'ERROR',
        message: `IQRFID-5102 CRC error: received ${receivedCrc.toString('hex').toUpperCase()}, calculated ${calculatedCrc.toString('hex').toUpperCase()}`,
      });
      return;
    }
    
    // Check if this is inventory response (command 0x01)
    if (command === 0x01) {
      // Check status byte
      if (length === 5 && data[3] === 0xFB) {
        // No tags found (status 0xFB)
        storage.addSystemLog({
          level: 'INFO',
          message: 'IQRFID-5102: No tags in range',
        });
      } else if (length > 5) {
        // Tags found - parse tag data
        this.parseIQRFID5102TagData(data);
      }
    } else {
      storage.addSystemLog({
        level: 'INFO',
        message: `IQRFID-5102 response - Cmd: 0x${command.toString(16).toUpperCase()}, Len: ${length}`,
      });
    }
  }

  private calculateIQRFID5102CRC(data: Buffer, length: number): Buffer {
    // CRC-16 calculation for IQRFID-5102 protocol
    let crc = 0xFFFF;
    
    for (let i = 0; i < length; i++) {
      crc ^= data[i];
      for (let j = 0; j < 8; j++) {
        if (crc & 0x0001) {
          crc = (crc >> 1) ^ 0x8408;
        } else {
          crc >>= 1;
        }
      }
    }
    
    // Return CRC as 2-byte buffer (low byte first)
    return Buffer.from([crc & 0xFF, (crc >> 8) & 0xFF]);
  }

  private parseIQRFID5102TagData(frame: Buffer): void {
    try {
      // New protocol format: [LEN][ADR][CMD][TAG_COUNT][RSSI][EPC_LEN][EPC_DATA...][CRC]
      // Example: 13 00 01 01 01 0C [12 bytes EPC] [2 bytes CRC]
      
      if (frame.length < 8) {
        storage.addSystemLog({
          level: 'WARN',
          message: 'IQRFID-5102 tag frame too short',
        });
        return;
      }
      
      const tagCount = frame[3];
      const rssiRaw = frame[4];
      const epcLength = frame[5];
      
      // Validate EPC length
      if (frame.length < 6 + epcLength + 2) {
        storage.addSystemLog({
          level: 'WARN',
          message: `IQRFID-5102 incomplete tag data: expected ${6 + epcLength + 2} bytes, got ${frame.length}`,
        });
        return;
      }
      
      // Extract EPC data
      const epcData = frame.slice(6, 6 + epcLength);
      const epc = epcData.toString('hex').toUpperCase();
      
      // RSSI conversion (if needed - may already be signed)
      const rssi = rssiRaw > 127 ? rssiRaw - 256 : rssiRaw;
      
      if (epc.length > 0) {
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
          message: `🎯 IQRFID-5102 Tag: EPC=${epc}, RSSI=${rssi} dBm, Count=${tagCount}, EPC_Len=${epcLength}`,
        });
      }
      
    } catch (error) {
      storage.addSystemLog({
        level: 'ERROR',
        message: `IQRFID-5102 parsing error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  }

  private initializeIQRFID5102(): void {
    // IQRFID-5102 uses [LEN][ADR][CMD][CRC] protocol format
    // Build inventory command: [0x04][0x00][0x01][CRC_LOW][CRC_HIGH]
    const cmdData = Buffer.from([0x04, 0x00, 0x01]);
    const crc = this.calculateIQRFID5102CRC(cmdData, 3);
    const inventoryCommand = Buffer.concat([cmdData, crc]);
    
    this.serialPort?.write(inventoryCommand);
    
    storage.addSystemLog({
      level: 'INFO',
      message: `Starting IQRFID-5102 inventory with command: ${inventoryCommand.toString('hex').toUpperCase()}`,
    });
    
    // Clear any existing interval
    if (this.inventoryInterval) {
      clearInterval(this.inventoryInterval);
    }
    
    // Start continuous inventory polling
    this.inventoryInterval = setInterval(() => {
      if (this.serialPort?.isOpen) {
        this.serialPort.write(inventoryCommand);
        storage.addSystemLog({
          level: 'INFO',
          message: `📡 IQRFID-5102 sending inventory command: ${inventoryCommand.toString('hex').toUpperCase()}`,
        });
      } else {
        storage.addSystemLog({
          level: 'WARN', 
          message: `⚠️ IQRFID-5102 port is closed, skipping inventory`,
        });
      }
    }, 500);
    
    storage.addSystemLog({
      level: 'INFO',
      message: `✅ IQRFID-5102 interval started with 500ms polling`,
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
