/**
 * Operation Queue — sequential processing of cabinet operations.
 *
 * When the cabinet is busy, incoming operations are queued and processed
 * one at a time in FIFO order.
 */
import { randomUUID } from 'crypto';

export interface QueuedOperation {
  id: string;
  type: 'issue' | 'return' | 'extract' | 'load';
  params: any;
  userId: string;
  addedAt: Date;
  status: 'pending' | 'running' | 'done' | 'failed';
  error?: string;
}

export class OperationQueue {
  private queue: QueuedOperation[] = [];
  private processing = false;
  private processor: ((op: QueuedOperation) => Promise<any>) | null = null;

  /**
   * Register a function that actually executes an operation.
   * The processor receives the operation and should throw on failure.
   */
  setProcessor(fn: (op: QueuedOperation) => Promise<any>) {
    this.processor = fn;
  }

  add(op: Omit<QueuedOperation, 'id' | 'addedAt' | 'status'>): string {
    const id = randomUUID();
    const queued: QueuedOperation = {
      ...op,
      id,
      addedAt: new Date(),
      status: 'pending',
    };
    this.queue.push(queued);

    // Kick off processing if idle
    if (!this.processing) {
      this.processNext().catch((err) =>
        console.error('[OperationQueue] processNext error:', err),
      );
    }

    return id;
  }

  getAll(): QueuedOperation[] {
    return [...this.queue];
  }

  getPosition(id: string): number {
    const idx = this.queue.findIndex((o) => o.id === id);
    return idx === -1 ? -1 : idx;
  }

  getById(id: string): QueuedOperation | undefined {
    return this.queue.find((o) => o.id === id);
  }

  isProcessing(): boolean {
    return this.processing;
  }

  async processNext(): Promise<void> {
    if (this.processing) return;

    const next = this.queue.find((o) => o.status === 'pending');
    if (!next) return;

    this.processing = true;
    next.status = 'running';

    try {
      if (this.processor) {
        await this.processor(next);
      }
      next.status = 'done';
    } catch (err: any) {
      next.status = 'failed';
      next.error = err?.message || String(err);
    } finally {
      this.processing = false;
    }

    // Purge completed operations older than 5 minutes
    const cutoff = Date.now() - 5 * 60 * 1000;
    this.queue = this.queue.filter(
      (o) =>
        o.status === 'pending' ||
        o.status === 'running' ||
        o.addedAt.getTime() > cutoff,
    );

    // Continue with next pending
    const hasMore = this.queue.some((o) => o.status === 'pending');
    if (hasMore) {
      await this.processNext();
    }
  }
}

export const operationQueue = new OperationQueue();
