import { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import type { User, Book, SystemStatus } from "@shared/schema";
import { 
  BookOpen, 
  Undo2, 
  User as UserIcon, 
  Shield, 
  Settings,
  CreditCard,
  CheckCircle2,
  XCircle,
  Loader2,
  ArrowLeft,
  Library,
  Package,
  AlertTriangle
} from "lucide-react";

type Screen = 
  | 'welcome' 
  | 'role_select' 
  | 'reader_menu' 
  | 'librarian_menu' 
  | 'admin_menu'
  | 'book_list' 
  | 'return_book' 
  | 'progress' 
  | 'success' 
  | 'error'
  | 'maintenance';

interface SessionData {
  user: User;
  reservedBooks: Book[];
  needsExtraction: number;
}

export default function KioskPage() {
  const [screen, setScreen] = useState<Screen>('welcome');
  const [session, setSession] = useState<SessionData | null>(null);
  const [progressMessage, setProgressMessage] = useState('');
  const [progressValue, setProgressValue] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const { toast } = useToast();

  const { data: systemStatus } = useQuery<SystemStatus>({
    queryKey: ['/api/status'],
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (systemStatus?.maintenanceMode && screen !== 'maintenance') {
      setScreen('maintenance');
    }
  }, [systemStatus?.maintenanceMode, screen]);

  const authMutation = useMutation({
    mutationFn: async (rfid: string) => {
      const response = await apiRequest('POST', '/api/auth/card', { rfid });
      return response.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        setSession({
          user: data.user,
          reservedBooks: data.reservedBooks || [],
          needsExtraction: data.needsExtraction || 0,
        });
        
        switch (data.user.role) {
          case 'admin':
            setScreen('admin_menu');
            break;
          case 'librarian':
            setScreen('librarian_menu');
            break;
          default:
            setScreen('reader_menu');
        }
      }
    },
    onError: (error: any) => {
      setErrorMessage(error.message || 'Ошибка авторизации');
      setScreen('error');
    },
  });

  const issueMutation = useMutation({
    mutationFn: async ({ bookRfid, userRfid }: { bookRfid: string; userRfid: string }) => {
      const response = await apiRequest('POST', '/api/issue', { bookRfid, userRfid });
      return response.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        setSuccessMessage(`Книга "${data.book.title}" выдана`);
        setScreen('success');
        queryClient.invalidateQueries({ queryKey: ['/api/books'] });
        queryClient.invalidateQueries({ queryKey: ['/api/cells'] });
      }
    },
    onError: (error: any) => {
      setErrorMessage(error.message || 'Ошибка выдачи');
      setScreen('error');
    },
  });

  const handleCardScan = useCallback((rfid: string) => {
    authMutation.mutate(rfid);
  }, [authMutation]);

  const handleLogout = () => {
    setSession(null);
    setScreen('welcome');
  };

  const handleBack = () => {
    if (!session) {
      setScreen('welcome');
      return;
    }
    switch (session.user.role) {
      case 'admin':
        setScreen('admin_menu');
        break;
      case 'librarian':
        setScreen('librarian_menu');
        break;
      default:
        setScreen('reader_menu');
    }
  };

  const handleIssueBook = (book: Book) => {
    if (!session) return;
    setProgressMessage(`Выдача книги: ${book.title}`);
    setProgressValue(50);
    setScreen('progress');
    
    setTimeout(() => {
      issueMutation.mutate({ bookRfid: book.rfid, userRfid: session.user.rfid });
    }, 1000);
  };

  const renderHeader = () => {
    if (screen === 'welcome' || screen === 'maintenance') return null;
    
    return (
      <div className="fixed top-0 left-0 right-0 h-24 bg-slate-900 text-white flex items-center justify-between px-8 z-50" data-testid="header">
        <div className="flex items-center gap-4">
          {screen !== 'role_select' && (
            <Button 
              variant="ghost" 
              size="lg"
              className="text-white hover:bg-slate-800"
              onClick={handleBack}
              data-testid="button-back"
            >
              <ArrowLeft className="w-6 h-6 mr-2" />
              Назад
            </Button>
          )}
          <Library className="w-10 h-10" />
          <span className="text-2xl font-bold">Библиотечный шкаф</span>
        </div>
        
        <div className="flex items-center gap-6">
          {session && (
            <div className="flex items-center gap-3">
              <UserIcon className="w-6 h-6" />
              <span className="text-xl">{session.user.name}</span>
              <Badge variant={
                session.user.role === 'admin' ? 'destructive' : 
                session.user.role === 'librarian' ? 'secondary' : 'default'
              }>
                {session.user.role === 'admin' ? 'Администратор' : 
                 session.user.role === 'librarian' ? 'Библиотекарь' : 'Читатель'}
              </Badge>
            </div>
          )}
          
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${
              systemStatus?.state === 'idle' ? 'bg-green-500' :
              systemStatus?.state === 'busy' ? 'bg-yellow-500' :
              systemStatus?.state === 'error' ? 'bg-red-500' : 'bg-gray-500'
            }`} />
            <span className="text-sm">
              {systemStatus?.state === 'idle' ? 'Готов' :
               systemStatus?.state === 'busy' ? 'Занят' :
               systemStatus?.state === 'error' ? 'Ошибка' : 'Инициализация'}
            </span>
          </div>
          
          {session && (
            <Button 
              variant="outline" 
              onClick={handleLogout}
              className="border-white text-white hover:bg-white hover:text-slate-900"
              data-testid="button-logout"
            >
              Выход
            </Button>
          )}
        </div>
      </div>
    );
  };

  const renderWelcome = () => (
    <div className="min-h-screen bg-gradient-to-br from-slate-800 to-slate-900 flex flex-col items-center justify-center text-white p-8" data-testid="screen-welcome">
      <Library className="w-32 h-32 mb-8 text-blue-400" />
      <h1 className="text-6xl font-bold mb-4">Добро пожаловать!</h1>
      <p className="text-3xl text-slate-300 mb-16">Автоматический шкаф книговыдачи</p>
      
      <div className="bg-slate-700/50 rounded-3xl p-12 flex flex-col items-center">
        <CreditCard className="w-24 h-24 mb-6 text-blue-400 animate-pulse" />
        <p className="text-2xl mb-4">Приложите карту читателя</p>
        <p className="text-lg text-slate-400">или введите номер карты</p>
        
        <div className="mt-8 flex gap-4">
          <Button 
            size="lg" 
            className="h-16 px-8 text-xl"
            onClick={() => handleCardScan('CARD001')}
            data-testid="button-test-reader"
          >
            Тест: Читатель
          </Button>
          <Button 
            size="lg" 
            variant="secondary"
            className="h-16 px-8 text-xl"
            onClick={() => handleCardScan('ADMIN01')}
            data-testid="button-test-librarian"
          >
            Тест: Библиотекарь
          </Button>
          <Button 
            size="lg" 
            variant="outline"
            className="h-16 px-8 text-xl border-white text-white hover:bg-white hover:text-slate-900"
            onClick={() => handleCardScan('ADMIN99')}
            data-testid="button-test-admin"
          >
            Тест: Админ
          </Button>
        </div>
      </div>
      
      {authMutation.isPending && (
        <div className="mt-8 flex items-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Авторизация...</span>
        </div>
      )}
    </div>
  );

  const renderReaderMenu = () => (
    <div className="min-h-screen bg-slate-100 pt-32 p-8" data-testid="screen-reader-menu">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-4xl font-bold text-slate-800 mb-8 text-center">Выберите действие</h2>
        
        <div className="grid grid-cols-2 gap-8">
          <Card 
            className="cursor-pointer hover:shadow-lg transition-shadow border-2 hover:border-blue-500"
            onClick={() => setScreen('book_list')}
            data-testid="card-get-book"
          >
            <CardContent className="p-12 flex flex-col items-center text-center">
              <BookOpen className="w-24 h-24 text-blue-500 mb-6" />
              <h3 className="text-3xl font-bold mb-3">Забрать книгу</h3>
              <p className="text-xl text-slate-500">
                {session?.reservedBooks.length 
                  ? `У вас ${session.reservedBooks.length} забронированных книг`
                  : 'Нет забронированных книг'}
              </p>
              {session && session.reservedBooks.length > 0 && (
                <Badge className="mt-4 text-lg px-4 py-2" variant="default">
                  {session.reservedBooks.length} книг
                </Badge>
              )}
            </CardContent>
          </Card>

          <Card 
            className="cursor-pointer hover:shadow-lg transition-shadow border-2 hover:border-green-500"
            onClick={() => setScreen('return_book')}
            data-testid="card-return-book"
          >
            <CardContent className="p-12 flex flex-col items-center text-center">
              <Undo2 className="w-24 h-24 text-green-500 mb-6" />
              <h3 className="text-3xl font-bold mb-3">Вернуть книгу</h3>
              <p className="text-xl text-slate-500">
                Положите книгу в окно приёма
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );

  const renderLibrarianMenu = () => (
    <div className="min-h-screen bg-slate-100 pt-32 p-8" data-testid="screen-librarian-menu">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-4xl font-bold text-slate-800 mb-8 text-center">Меню библиотекаря</h2>
        
        {session && session.needsExtraction > 0 && (
          <div className="mb-8 p-6 bg-yellow-100 border-2 border-yellow-400 rounded-xl flex items-center justify-between">
            <div className="flex items-center gap-4">
              <AlertTriangle className="w-8 h-8 text-yellow-600" />
              <span className="text-xl font-medium">
                {session.needsExtraction} книг требуют изъятия
              </span>
            </div>
            <Button size="lg" variant="default" data-testid="button-extract-all">
              Изъять все
            </Button>
          </div>
        )}
        
        <div className="grid grid-cols-3 gap-6">
          <Card className="cursor-pointer hover:shadow-lg transition-shadow" data-testid="card-load-books">
            <CardContent className="p-8 flex flex-col items-center text-center">
              <Package className="w-16 h-16 text-blue-500 mb-4" />
              <h3 className="text-2xl font-bold mb-2">Загрузить книги</h3>
              <p className="text-slate-500">Добавить книги в шкаф</p>
            </CardContent>
          </Card>

          <Card className="cursor-pointer hover:shadow-lg transition-shadow" data-testid="card-unload-books">
            <CardContent className="p-8 flex flex-col items-center text-center">
              <Undo2 className="w-16 h-16 text-orange-500 mb-4" />
              <h3 className="text-2xl font-bold mb-2">Изъять книги</h3>
              <p className="text-slate-500">Забрать возвращённые книги</p>
            </CardContent>
          </Card>

          <Card className="cursor-pointer hover:shadow-lg transition-shadow" data-testid="card-inventory">
            <CardContent className="p-8 flex flex-col items-center text-center">
              <BookOpen className="w-16 h-16 text-green-500 mb-4" />
              <h3 className="text-2xl font-bold mb-2">Инвентаризация</h3>
              <p className="text-slate-500">Проверить содержимое</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );

  const renderAdminMenu = () => {
    const [, setLocation] = useLocation();
    
    return (
      <div className="min-h-screen bg-slate-100 pt-32 p-8" data-testid="screen-admin-menu">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-4xl font-bold text-slate-800 mb-8 text-center">Администрирование</h2>
          
          <div className="grid grid-cols-3 gap-6">
            <Card 
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setLocation('/admin')}
              data-testid="card-admin-dashboard"
            >
              <CardContent className="p-8 flex flex-col items-center text-center">
                <Settings className="w-16 h-16 text-slate-600 mb-4" />
                <h3 className="text-2xl font-bold mb-2">Dashboard</h3>
                <p className="text-slate-500">Статистика и мониторинг</p>
              </CardContent>
            </Card>

            <Card className="cursor-pointer hover:shadow-lg transition-shadow" data-testid="card-diagnostics">
              <CardContent className="p-8 flex flex-col items-center text-center">
                <Shield className="w-16 h-16 text-blue-500 mb-4" />
                <h3 className="text-2xl font-bold mb-2">Диагностика</h3>
                <p className="text-slate-500">Проверка оборудования</p>
              </CardContent>
            </Card>

            <Card className="cursor-pointer hover:shadow-lg transition-shadow" data-testid="card-calibration">
              <CardContent className="p-8 flex flex-col items-center text-center">
                <Settings className="w-16 h-16 text-purple-500 mb-4" />
                <h3 className="text-2xl font-bold mb-2">Калибровка</h3>
                <p className="text-slate-500">Настройка механики</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  };

  const renderBookList = () => (
    <div className="min-h-screen bg-slate-100 pt-32 p-8" data-testid="screen-book-list">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-4xl font-bold text-slate-800 mb-8">Ваши забронированные книги</h2>
        
        {session?.reservedBooks.length === 0 ? (
          <Card className="p-12 text-center">
            <BookOpen className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <p className="text-2xl text-slate-500">Нет забронированных книг</p>
          </Card>
        ) : (
          <div className="space-y-4">
            {session?.reservedBooks.map((book) => (
              <Card key={book.id} className="p-6" data-testid={`card-book-${book.rfid}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-2xl font-bold">{book.title}</h3>
                    <p className="text-lg text-slate-500">{book.author}</p>
                    {book.isbn && <p className="text-sm text-slate-400">ISBN: {book.isbn}</p>}
                  </div>
                  <Button 
                    size="lg" 
                    className="h-16 px-8 text-xl"
                    onClick={() => handleIssueBook(book)}
                    data-testid={`button-issue-${book.rfid}`}
                  >
                    <BookOpen className="w-6 h-6 mr-2" />
                    Забрать
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const renderReturnBook = () => (
    <div className="min-h-screen bg-slate-100 pt-32 p-8" data-testid="screen-return-book">
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-4xl font-bold text-slate-800 mb-8">Возврат книги</h2>
        
        <Card className="p-12">
          <Package className="w-24 h-24 text-green-500 mx-auto mb-6" />
          <p className="text-2xl mb-4">Положите книгу в окно приёма</p>
          <p className="text-lg text-slate-500 mb-8">
            Книга будет автоматически распознана по RFID-метке
          </p>
          
          <div className="h-2 bg-slate-200 rounded-full overflow-hidden mb-8">
            <div className="h-full bg-green-500 animate-pulse" style={{ width: '30%' }} />
          </div>
          
          <p className="text-slate-500">Ожидание книги...</p>
        </Card>
      </div>
    </div>
  );

  const renderProgress = () => (
    <div className="min-h-screen bg-slate-100 pt-32 flex items-center justify-center" data-testid="screen-progress">
      <Card className="p-12 w-full max-w-2xl text-center">
        <Loader2 className="w-24 h-24 text-blue-500 mx-auto mb-6 animate-spin" />
        <h2 className="text-3xl font-bold mb-4">{progressMessage}</h2>
        <Progress value={progressValue} className="h-4 mb-4" />
        <p className="text-slate-500">Пожалуйста, подождите...</p>
      </Card>
    </div>
  );

  const renderSuccess = () => (
    <div className="min-h-screen bg-green-50 pt-32 flex items-center justify-center" data-testid="screen-success">
      <Card className="p-12 w-full max-w-2xl text-center border-green-500 border-2">
        <CheckCircle2 className="w-32 h-32 text-green-500 mx-auto mb-6" />
        <h2 className="text-4xl font-bold text-green-700 mb-4">Успешно!</h2>
        <p className="text-2xl text-slate-600 mb-8">{successMessage}</p>
        <Button 
          size="lg" 
          className="h-16 px-12 text-xl"
          onClick={handleBack}
          data-testid="button-continue"
        >
          Продолжить
        </Button>
      </Card>
    </div>
  );

  const renderError = () => (
    <div className="min-h-screen bg-red-50 pt-32 flex items-center justify-center" data-testid="screen-error">
      <Card className="p-12 w-full max-w-2xl text-center border-red-500 border-2">
        <XCircle className="w-32 h-32 text-red-500 mx-auto mb-6" />
        <h2 className="text-4xl font-bold text-red-700 mb-4">Ошибка</h2>
        <p className="text-2xl text-slate-600 mb-8">{errorMessage}</p>
        <Button 
          size="lg" 
          variant="destructive"
          className="h-16 px-12 text-xl"
          onClick={handleBack}
          data-testid="button-back-error"
        >
          Назад
        </Button>
      </Card>
    </div>
  );

  const renderMaintenance = () => (
    <div className="min-h-screen bg-yellow-50 flex items-center justify-center" data-testid="screen-maintenance">
      <Card className="p-12 w-full max-w-2xl text-center border-yellow-500 border-2">
        <AlertTriangle className="w-32 h-32 text-yellow-500 mx-auto mb-6" />
        <h2 className="text-4xl font-bold text-yellow-700 mb-4">Шкаф временно недоступен</h2>
        <p className="text-2xl text-slate-600">Ведутся технические работы</p>
      </Card>
    </div>
  );

  return (
    <>
      {renderHeader()}
      {screen === 'welcome' && renderWelcome()}
      {screen === 'reader_menu' && renderReaderMenu()}
      {screen === 'librarian_menu' && renderLibrarianMenu()}
      {screen === 'admin_menu' && renderAdminMenu()}
      {screen === 'book_list' && renderBookList()}
      {screen === 'return_book' && renderReturnBook()}
      {screen === 'progress' && renderProgress()}
      {screen === 'success' && renderSuccess()}
      {screen === 'error' && renderError()}
      {screen === 'maintenance' && renderMaintenance()}
    </>
  );
}
