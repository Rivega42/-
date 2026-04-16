import type { User, Book, Cell, SystemStatus, Statistics, CalibrationData } from "@shared/schema";

export type Screen =
  | 'welcome'
  | 'reader_menu'
  | 'librarian_menu'
  | 'admin_menu'
  | 'book_list'
  | 'return_book'
  | 'issue_process'
  | 'load_books'
  | 'extract_books'
  | 'inventory'
  | 'operations_log'
  | 'statistics'
  | 'diagnostics'
  | 'mechanics_test'
  | 'calibration'
  | 'cabinet_view'
  | 'settings'
  | 'teach_mode'
  | 'progress'
  | 'success'
  | 'error'
  | 'maintenance';

export interface SessionData {
  user: User;
  reservedBooks: Book[];
  needsExtraction: number;
}

export interface KioskActions {
  setScreen: (screen: Screen) => void;
  setSession: (session: SessionData | null) => void;
  setProgressMessage: (msg: string) => void;
  setProgressValue: (val: number) => void;
  setErrorMessage: (msg: string) => void;
  setSuccessMessage: (msg: string) => void;
}

export interface KioskState {
  screen: Screen;
  session: SessionData | null;
  systemStatus: SystemStatus | undefined;
  progressMessage: string;
  progressValue: number;
  errorMessage: string;
  successMessage: string;
}
