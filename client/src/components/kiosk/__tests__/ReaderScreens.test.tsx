import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ReaderMenu, BookList } from '../ReaderScreens';
import type { Book, User } from '@shared/schema';

const mockUser = {
  id: 'user-1',
  rfid: 'CARD001',
  name: 'Иван Иванов',
  role: 'reader',
  email: null,
  phone: null,
  blocked: false,
  createdAt: new Date(),
} as unknown as User;

const mockBook = {
  id: 'book-1',
  rfid: 'BOOK001',
  title: 'Война и мир',
  author: 'Л.Н. Толстой',
  isbn: null,
  status: 'reserved',
  cellId: null,
  reservedForRfid: 'CARD001',
  issuedToRfid: null,
  createdAt: new Date(),
  updatedAt: new Date(),
} as unknown as Book;

describe('ReaderMenu', () => {
  it('renders greeting with user name', () => {
    render(
      <ReaderMenu
        session={{ user: mockUser, reservedBooks: [], needsExtraction: 0 }}
        onGetBooks={() => {}}
        onReturnBook={() => {}}
      />
    );
    expect(screen.getByText(/Иван Иванов/)).toBeInTheDocument();
  });

  it('calls onGetBooks when the get-book card is clicked', () => {
    const onGetBooks = vi.fn();
    render(
      <ReaderMenu
        session={{ user: mockUser, reservedBooks: [mockBook], needsExtraction: 0 }}
        onGetBooks={onGetBooks}
        onReturnBook={() => {}}
      />
    );
    fireEvent.click(screen.getByTestId('card-get-book'));
    expect(onGetBooks).toHaveBeenCalled();
  });

  it('card-get-book is keyboard activatable via Enter', () => {
    const onGetBooks = vi.fn();
    render(
      <ReaderMenu
        session={{ user: mockUser, reservedBooks: [], needsExtraction: 0 }}
        onGetBooks={onGetBooks}
        onReturnBook={() => {}}
      />
    );
    const card = screen.getByTestId('card-get-book');
    expect(card).toHaveAttribute('role', 'button');
    expect(card).toHaveAttribute('tabindex', '0');
    fireEvent.keyDown(card, { key: 'Enter' });
    expect(onGetBooks).toHaveBeenCalled();
  });
});

describe('BookList', () => {
  it('renders empty state when no books', () => {
    render(
      <BookList
        books={[]}
        onIssue={() => {}}
        userRfid="CARD001"
        issuing={false}
      />
    );
    expect(screen.getByText(/Нет забронированных книг/)).toBeInTheDocument();
  });

  it('calls onIssue with correct args when receive clicked', () => {
    const onIssue = vi.fn();
    render(
      <BookList
        books={[mockBook]}
        onIssue={onIssue}
        userRfid="CARD001"
        issuing={false}
      />
    );
    fireEvent.click(screen.getByTestId('button-issue-BOOK001'));
    expect(onIssue).toHaveBeenCalledWith('BOOK001', 'CARD001');
  });

  it('disables issue button when issuing is true', () => {
    render(
      <BookList
        books={[mockBook]}
        onIssue={() => {}}
        userRfid="CARD001"
        issuing={true}
      />
    );
    expect(screen.getByTestId('button-issue-BOOK001')).toBeDisabled();
  });
});
