import { SerialPort } from 'serialport';
import { ReadlineParser } from '@serialport/parser-readline';
import EventEmitter from 'events';
import { storage } from '../storage';
import type { TagReadEvent, RfidReaderStatus } from '@shared/schema';

export class RfidService extends EventEmitter {
  private serialPort?: SerialPort;
  private parser?: ReadlineParser;
  private isConnected = false;
  private currentPort?: string;

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

  async connect(portPath: string, baudRate: number = 57600): Promise<void> {
    if (this.isConnected) {
      await this.disconnect();
    }

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
        this.emit('status', {
          connected: true,
          port: portPath,
        } as RfidReaderStatus);
        
        storage.addSystemLog({
          level: 'SUCCESS',
          message: `Connected to RRU9816 on port ${portPath}`,
        });

        // Initialize reader - send inventory command
        this.startInventory();
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

  private startInventory(): void {
    if (!this.serialPort || !this.serialPort.isOpen) return;

    // Send inventory command - this would be specific to RRU9816 protocol
    // For now, using a generic approach
    try {
      // Most UHF RFID readers use commands like this
      // Actual RRU9816 might need specific hex commands
      const inventoryCommand = Buffer.from([0xA0, 0x03, 0x01, 0x89, 0x01, 0x8D]); // Example command
      this.serialPort.write(inventoryCommand);
      
      storage.addSystemLog({
        level: 'INFO',
        message: 'Starting RFID inventory scan...',
      });
    } catch (error) {
      storage.addSystemLog({
        level: 'ERROR',
        message: `Failed to start inventory: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  }

  public manualInventory(): void {
    this.startInventory();
  }

  public getConnectionStatus(): RfidReaderStatus {
    return {
      connected: this.isConnected,
      port: this.currentPort,
    };
  }
}

export const rfidService = new RfidService();
