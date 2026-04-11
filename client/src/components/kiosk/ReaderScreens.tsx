import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BookOpen, Undo2, CreditCard, Loader2 } from "lucide-react";
import type { User, Book } from "@shared/schema";
import type { SessionData } from "./types";

interface ReaderMenuProps {
  session: SessionData | null;
  onGetBooks: () => void;
  onReturnBook: () => void;
}

export function ReaderMenu({ session, onGetBooks, onReturnBook }: ReaderMenuProps) {
  return (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-reader-menu">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-3xl font-bold text-slate-800 mb-2 text-center">
          Здравствуйте, {session?.user.name}!
        </h2>
        {(session?.reservedBooks?.length ?? 0) > 0 && (
          <p className="text-center text-slate-500 mb-6">
            У вас {session?.reservedBooks.length} забронированных книг
          </p>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <Card
            className="cursor-pointer hover:shadow-xl transition-all active:scale-[0.98]"
            onClick={onGetBooks}
            data-testid="card-get-book"
          >
            <CardContent className="p-8 sm:p-10 flex flex-col items-center text-center">
              <BookOpen className="w-16 h-16 sm:w-20 sm:h-20 text-blue-500 mb-4" />
              <h3 className="text-2xl font-bold mb-2">Получить книгу</h3>
              <p className="text-slate-500">Забронированные книги</p>
              {(session?.reservedBooks?.length ?? 0) > 0 && (
                <Badge className="mt-3 text-lg px-4 py-1">{session?.reservedBooks.length}</Badge>
              )}
            </CardContent>
          </Card>

          <Card
            className="cursor-pointer hover:shadow-xl transition-all active:scale-[0.98]"
            onClick={onReturnBook}
            data-testid="card-return-book"
          >
            <CardContent className="p-8 sm:p-10 flex flex-col items-center text-center">
              <Undo2 className="w-16 h-16 sm:w-20 sm:h-20 text-green-500 mb-4" />
              <h3 className="text-2xl font-bold mb-2">Вернуть книгу</h3>
              <p className="text-slate-500">Поднесите книгу к считывателю</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

interface BookListProps {
  books: Book[];
  onIssue: (bookRfid: string, userRfid: string) => void;
  userRfid: string;
  issuing: boolean;
}

export function BookList({ books, onIssue, userRfid, issuing }: BookListProps) {
  return (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-book-list">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-slate-800 mb-6">Ваши забронированные книги</h2>

        {books.length === 0 ? (
          <Card className="p-10 text-center">
            <BookOpen className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <p className="text-xl text-slate-500">Нет забронированных книг</p>
          </Card>
        ) : (
          <div className="space-y-4">
            {books.map((book) => (
              <Card key={book.id} className="p-5" data-testid={`card-book-${book.rfid}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xl font-bold">{book.title}</h3>
                    <p className="text-base text-slate-500">{book.author}</p>
                  </div>
                  <Button
                    size="lg"
                    className="h-14 px-8 text-lg"
                    onClick={() => onIssue(book.rfid, userRfid)}
                    disabled={issuing}
                    data-testid={`button-issue-${book.rfid}`}
                  >
                    {issuing ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : null}
                    Получить
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface ReturnBookProps {
  isPending: boolean;
}

export function ReturnBook({ isPending }: ReturnBookProps) {
  return (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-return-book">
      <div className="max-w-3xl mx-auto text-center">
        <CreditCard className="w-24 h-24 text-green-500 mx-auto mb-6 animate-pulse" />
        <h2 className="text-3xl font-bold text-slate-800 mb-4">Возврат книги</h2>
        <p className="text-xl text-slate-500 mb-8">Поднесите книгу к считывателю внутри шкафа</p>
        {isPending && (
          <div className="flex items-center justify-center gap-3 text-slate-600">
            <Loader2 className="w-6 h-6 animate-spin" />
            <span>Обработка...</span>
          </div>
        )}
      </div>
    </div>
  );
}
