/**
 * PythonBridgeService — extracted from the inline runPythonBridge in routes.ts.
 *
 * Encapsulates communication with the Python backend via the bridge.py script.
 * Each method spawns a subprocess, collects JSON output, and returns the result.
 *
 * Future migration plan:
 * ─────────────────────
 * This service currently communicates via child_process spawn + stdout JSON.
 * A future version should use a persistent Unix domain socket so that:
 *   1. The Python backend stays alive between requests (no startup cost).
 *   2. Real-time progress events flow over the socket instead of stdout parsing.
 *   3. The Node server can push commands (e.g. emergency-stop) instantly.
 * The socket path would be /tmp/bookcabinet.sock or configurable via env.
 */
import { spawn } from 'child_process';

export class PythonBridgeService {
  private bridgePath: string;
  private cwd: string;
  private timeoutMs: number;

  constructor() {
    this.bridgePath =
      process.env.PYTHON_BRIDGE_PATH ||
      '/home/admin42/bookcabinet/bookcabinet/bridge.py';
    this.cwd = process.env.PYTHON_BRIDGE_CWD || '/home/admin42/bookcabinet';
    this.timeoutMs = 120_000;
  }

  /**
   * Low-level: run a bridge command and return the parsed result.
   * Emits progress messages via the optional broadcast callback.
   */
  async execute(
    command: string,
    args: string[],
    onProgress?: (msg: any) => void,
  ): Promise<{ success: boolean; [key: string]: any }> {
    return new Promise((resolve, reject) => {
      const proc = spawn('python3', [this.bridgePath, command, ...args], {
        cwd: this.cwd,
        timeout: this.timeoutMs,
      });

      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (data: Buffer) => {
        stdout += data.toString();
        const lines = stdout.split('\n');
        stdout = lines.pop() || '';
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const msg = JSON.parse(line);
            if (msg.type === 'progress' && onProgress) {
              onProgress(msg);
            }
          } catch {
            // non-JSON line, ignore
          }
        }
      });

      proc.stderr.on('data', (data: Buffer) => {
        stderr += data.toString();
      });

      proc.on('close', (code: number) => {
        // Parse remaining stdout
        if (stdout.trim()) {
          try {
            const msg = JSON.parse(stdout.trim());
            if (msg.type === 'result') {
              resolve(msg);
              return;
            }
          } catch {
            // ignore
          }
        }
        if (code !== 0) {
          reject(
            new Error(stderr || `Python bridge exited with code ${code}`),
          );
        } else {
          resolve({ success: false, message: 'No result from Python bridge' });
        }
      });
    });
  }

  async issue(
    bookRfid: string,
    userRfid: string,
    onProgress?: (msg: any) => void,
  ): Promise<any> {
    return this.execute('issue', [bookRfid, userRfid], onProgress);
  }

  async returnBook(
    bookRfid: string,
    onProgress?: (msg: any) => void,
  ): Promise<any> {
    return this.execute('return', [bookRfid], onProgress);
  }

  async home(onProgress?: (msg: any) => void): Promise<any> {
    return this.execute('home', [], onProgress);
  }

  async stop(): Promise<any> {
    return this.execute('stop', []);
  }

  async status(): Promise<any> {
    return this.execute('status', []);
  }

  async issueSequence(
    cellAddress: string,
    onProgress?: (msg: any) => void,
  ): Promise<any> {
    return this.execute('issue_sequence', [cellAddress], onProgress);
  }

  async returnSequence(
    cellAddress: string,
    onProgress?: (msg: any) => void,
  ): Promise<any> {
    return this.execute('return_sequence', [cellAddress], onProgress);
  }
}

export const pythonBridge = new PythonBridgeService();
