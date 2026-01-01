import { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import type { User, Book, Cell, SystemStatus, Operation, Statistics, CalibrationData } from "@shared/schema";
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
  AlertTriangle,
  Search,
  Plus,
  History,
  BarChart3,
  Activity,
  Cog,
  Play,
  RotateCcw,
  Move,
  Lock,
  Unlock,
  Target,
  Home,
  ArrowUp,
  ArrowDown,
  ArrowRight
} from "lucide-react";

type Screen = 
  | 'welcome' 
  | 'reader_menu' 
  | 'librarian_menu' 
  | 'admin_menu'
  | 'book_list' 
  | 'return_book' 
  | 'load_books'
  | 'extract_books'
  | 'inventory'
  | 'operations_log'
  | 'statistics'
  | 'diagnostics'
  | 'mechanics_test'
  | 'calibration'
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
  const [newBookRfid, setNewBookRfid] = useState('');
  const [newBookTitle, setNewBookTitle] = useState('');
  const [newBookAuthor, setNewBookAuthor] = useState('');
  const [, setLocation] = useLocation();
  const { toast } = useToast();

  const { data: systemStatus } = useQuery<SystemStatus>({
    queryKey: ['/api/status'],
    refetchInterval: 3000,
  });

  const { data: cellsNeedingExtraction = [] } = useQuery<Cell[]>({
    queryKey: ['/api/cells/extraction'],
    enabled: session?.user.role === 'librarian' || session?.user.role === 'admin',
  });

  const { data: allCells = [] } = useQuery<Cell[]>({
    queryKey: ['/api/cells'],
    enabled: screen === 'extract_books',
  });

  const { data: statistics } = useQuery<Statistics>({
    queryKey: ['/api/statistics'],
    enabled: screen === 'statistics',
  });

  const { data: operations = [] } = useQuery<Operation[]>({
    queryKey: ['/api/operations'],
    enabled: screen === 'operations_log',
  });

  const { data: diagnostics } = useQuery<{ sensors: Record<string, boolean>; motors: string; rfid: Record<string, string> }>({
    queryKey: ['/api/diagnostics'],
    enabled: screen === 'diagnostics' || screen === 'mechanics_test',
  });

  const { data: calibration, refetch: refetchCalibration } = useQuery<CalibrationData>({
    queryKey: ['/api/calibration'],
    enabled: screen === 'calibration',
  });

  useEffect(() => {
    if (systemStatus?.maintenanceMode && screen !== 'maintenance' && session?.user.role !== 'admin') {
      setScreen('maintenance');
    }
  }, [systemStatus?.maintenanceMode, screen, session]);

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

  const loadBookMutation = useMutation({
    mutationFn: async ({ bookRfid, title, author }: { bookRfid: string; title: string; author?: string }) => {
      const response = await apiRequest('POST', '/api/load-book', { bookRfid, title, author });
      return response.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        setSuccessMessage(`Книга загружена в ячейку`);
        setScreen('success');
        setNewBookRfid('');
        setNewBookTitle('');
        setNewBookAuthor('');
        queryClient.invalidateQueries({ queryKey: ['/api/books'] });
        queryClient.invalidateQueries({ queryKey: ['/api/cells'] });
      }
    },
    onError: (error: any) => {
      setErrorMessage(error.message || 'Ошибка загрузки книги');
      setScreen('error');
    },
  });

  const extractMutation = useMutation({
    mutationFn: async (cellId: number) => {
      const response = await apiRequest('POST', '/api/extract', { cellId });
      return response.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        toast({ title: 'Успешно', description: `Книга "${data.book?.title}" изъята` });
        queryClient.invalidateQueries({ queryKey: ['/api/cells'] });
        queryClient.invalidateQueries({ queryKey: ['/api/cells/extraction'] });
      }
    },
    onError: (error: any) => {
      toast({ title: 'Ошибка', description: error.message, variant: 'destructive' });
    },
  });

  const extractAllMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest('POST', '/api/extract-all', {});
      return response.json();
    },
    onSuccess: (data) => {
      setSuccessMessage(`Изъято ${data.extracted} книг`);
      setScreen('success');
      queryClient.invalidateQueries({ queryKey: ['/api/cells'] });
    },
    onError: (error: any) => {
      setErrorMessage(error.message || 'Ошибка изъятия');
      setScreen('error');
    },
  });

  const inventoryMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest('POST', '/api/run-inventory', {});
      return response.json();
    },
    onSuccess: (data) => {
      setSuccessMessage(`Инвентаризация завершена: найдено ${data.found} книг, отсутствует ${data.missing}`);
      setScreen('success');
    },
    onError: (error: any) => {
      setErrorMessage(error.message || 'Ошибка инвентаризации');
      setScreen('error');
    },
  });

  const testMotorMutation = useMutation({
    mutationFn: async (params: { command: string; axis?: string; steps?: number; speed?: number }) => {
      const response = await apiRequest('POST', '/api/test/motor', params);
      return response.json();
    },
    onSuccess: () => {
      toast({ title: 'Успех', description: 'Команда мотора выполнена' });
      queryClient.invalidateQueries({ queryKey: ['/api/diagnostics'] });
    },
    onError: (error: any) => {
      toast({ title: 'Ошибка', description: error.message, variant: 'destructive' });
    },
  });

  const testTrayMutation = useMutation({
    mutationFn: async (command: string) => {
      const response = await apiRequest('POST', '/api/test/tray', { command });
      return response.json();
    },
    onSuccess: () => {
      toast({ title: 'Успех', description: 'Команда лотка выполнена' });
    },
    onError: (error: any) => {
      toast({ title: 'Ошибка', description: error.message, variant: 'destructive' });
    },
  });

  const testServoMutation = useMutation({
    mutationFn: async (params: { servo: string; command: string }) => {
      const response = await apiRequest('POST', '/api/test/servo', params);
      return response.json();
    },
    onSuccess: () => {
      toast({ title: 'Успех', description: 'Команда сервопривода выполнена' });
      queryClient.invalidateQueries({ queryKey: ['/api/diagnostics'] });
    },
    onError: (error: any) => {
      toast({ title: 'Ошибка', description: error.message, variant: 'destructive' });
    },
  });

  const testShutterMutation = useMutation({
    mutationFn: async (params: { shutter: string; command: string }) => {
      const response = await apiRequest('POST', '/api/test/shutter', params);
      return response.json();
    },
    onSuccess: () => {
      toast({ title: 'Успех', description: 'Команда шторки выполнена' });
      queryClient.invalidateQueries({ queryKey: ['/api/diagnostics'] });
    },
    onError: (error: any) => {
      toast({ title: 'Ошибка', description: error.message, variant: 'destructive' });
    },
  });

  const saveCalibrationMutation = useMutation({
    mutationFn: async (data: Partial<CalibrationData>) => {
      const response = await apiRequest('POST', '/api/calibration', data);
      return response.json();
    },
    onSuccess: () => {
      toast({ title: 'Успех', description: 'Калибровка сохранена' });
      refetchCalibration();
    },
    onError: (error: any) => {
      toast({ title: 'Ошибка', description: error.message, variant: 'destructive' });
    },
  });

  const resetCalibrationMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest('POST', '/api/calibration/reset', {});
      return response.json();
    },
    onSuccess: () => {
      toast({ title: 'Успех', description: 'Калибровка сброшена к значениям по умолчанию' });
      refetchCalibration();
    },
    onError: (error: any) => {
      toast({ title: 'Ошибка', description: error.message, variant: 'destructive' });
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

  const handleLoadBook = () => {
    if (!newBookRfid || !newBookTitle) {
      toast({ title: 'Ошибка', description: 'Заполните RFID и название книги', variant: 'destructive' });
      return;
    }
    setProgressMessage(`Загрузка книги: ${newBookTitle}`);
    setProgressValue(30);
    setScreen('progress');
    
    loadBookMutation.mutate({ bookRfid: newBookRfid, title: newBookTitle, author: newBookAuthor || undefined });
  };

  const renderHeader = () => {
    if (screen === 'welcome' || screen === 'maintenance') return null;
    
    return (
      <div className="fixed top-0 left-0 right-0 h-20 bg-slate-900 text-white flex items-center justify-between px-6 z-50" data-testid="header">
        <div className="flex items-center gap-4">
          {!['reader_menu', 'librarian_menu', 'admin_menu'].includes(screen) && (
            <Button 
              variant="ghost" 
              size="lg"
              className="text-white hover:bg-slate-800 h-14 px-6 text-lg"
              onClick={handleBack}
              data-testid="button-back"
            >
              <ArrowLeft className="w-6 h-6 mr-2" />
              Назад
            </Button>
          )}
          <Library className="w-8 h-8" />
          <span className="text-xl font-bold">Библиотечный шкаф</span>
        </div>
        
        <div className="flex items-center gap-4">
          {session && (
            <div className="flex items-center gap-2">
              <UserIcon className="w-5 h-5" />
              <span className="text-lg">{session.user.name}</span>
              <Badge variant={
                session.user.role === 'admin' ? 'destructive' : 
                session.user.role === 'librarian' ? 'secondary' : 'default'
              }>
                {session.user.role === 'admin' ? 'Админ' : 
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
               systemStatus?.state === 'busy' ? 'Занят' : 'Ошибка'}
            </span>
          </div>
          
          {session && (
            <Button 
              variant="outline" 
              onClick={handleLogout}
              className="border-white text-white hover:bg-white hover:text-slate-900 h-12 px-6"
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
      <Library className="w-28 h-28 mb-6 text-blue-400" />
      <h1 className="text-5xl font-bold mb-3">Добро пожаловать!</h1>
      <p className="text-2xl text-slate-300 mb-12">Автоматический шкаф книговыдачи</p>
      
      <div className="bg-slate-700/50 rounded-2xl p-10 flex flex-col items-center max-w-2xl w-full">
        <CreditCard className="w-20 h-20 mb-4 text-blue-400 animate-pulse" />
        <p className="text-xl mb-2">Приложите карту читателя</p>
        <p className="text-base text-slate-400 mb-6">или выберите тестового пользователя</p>
        
        <div className="flex flex-wrap gap-3 justify-center">
          <Button 
            size="lg" 
            className="h-20 px-8 text-xl min-w-[200px]"
            onClick={() => handleCardScan('CARD001')}
            data-testid="button-test-reader"
          >
            <UserIcon className="w-6 h-6 mr-2" />
            Читатель
          </Button>
          <Button 
            size="lg" 
            variant="secondary"
            className="h-20 px-8 text-xl min-w-[200px]"
            onClick={() => handleCardScan('ADMIN01')}
            data-testid="button-test-librarian"
          >
            <BookOpen className="w-6 h-6 mr-2" />
            Библиотекарь
          </Button>
          <Button 
            size="lg" 
            variant="outline"
            className="h-20 px-8 text-xl min-w-[200px] border-white text-white hover:bg-white hover:text-slate-900"
            onClick={() => handleCardScan('ADMIN99')}
            data-testid="button-test-admin"
          >
            <Shield className="w-6 h-6 mr-2" />
            Администратор
          </Button>
        </div>
      </div>
      
      {authMutation.isPending && (
        <div className="mt-6 flex items-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Авторизация...</span>
        </div>
      )}
    </div>
  );

  const renderReaderMenu = () => (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-reader-menu">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-slate-800 mb-6 text-center">Выберите действие</h2>
        
        <div className="grid grid-cols-2 gap-6">
          <Card 
            className="cursor-pointer hover:shadow-xl transition-all border-2 hover:border-blue-500 active:scale-[0.98]"
            onClick={() => setScreen('book_list')}
            data-testid="card-get-book"
          >
            <CardContent className="p-10 flex flex-col items-center text-center">
              <BookOpen className="w-20 h-20 text-blue-500 mb-4" />
              <h3 className="text-2xl font-bold mb-2">Забрать книгу</h3>
              <p className="text-lg text-slate-500">
                {session?.reservedBooks.length 
                  ? `${session.reservedBooks.length} забронировано`
                  : 'Нет бронирований'}
              </p>
              {session && session.reservedBooks.length > 0 && (
                <Badge className="mt-3 text-base px-4 py-1" variant="default">
                  {session.reservedBooks.length} книг
                </Badge>
              )}
            </CardContent>
          </Card>

          <Card 
            className="cursor-pointer hover:shadow-xl transition-all border-2 hover:border-green-500 active:scale-[0.98]"
            onClick={() => setScreen('return_book')}
            data-testid="card-return-book"
          >
            <CardContent className="p-10 flex flex-col items-center text-center">
              <Undo2 className="w-20 h-20 text-green-500 mb-4" />
              <h3 className="text-2xl font-bold mb-2">Вернуть книгу</h3>
              <p className="text-lg text-slate-500">
                Положите книгу в окно приёма
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );

  const renderLibrarianMenu = () => (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-librarian-menu">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold text-slate-800 mb-6 text-center">Меню библиотекаря</h2>
        
        {session && session.needsExtraction > 0 && (
          <div className="mb-6 p-5 bg-yellow-100 border-2 border-yellow-400 rounded-xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-7 h-7 text-yellow-600" />
              <span className="text-lg font-medium">
                {session.needsExtraction} книг требуют изъятия
              </span>
            </div>
            <Button 
              size="lg" 
              variant="default" 
              className="h-14 px-6 text-lg"
              onClick={() => {
                setProgressMessage('Изъятие всех книг...');
                setProgressValue(20);
                setScreen('progress');
                extractAllMutation.mutate();
              }}
              disabled={extractAllMutation.isPending}
              data-testid="button-extract-all"
            >
              {extractAllMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : null}
              Изъять все
            </Button>
          </div>
        )}
        
        <div className="grid grid-cols-3 gap-5">
          <Card 
            className="cursor-pointer hover:shadow-xl transition-all active:scale-[0.98]"
            onClick={() => setScreen('load_books')}
            data-testid="card-load-books"
          >
            <CardContent className="p-7 flex flex-col items-center text-center">
              <Plus className="w-14 h-14 text-blue-500 mb-3" />
              <h3 className="text-xl font-bold mb-1">Загрузить книги</h3>
              <p className="text-slate-500">Добавить в шкаф</p>
            </CardContent>
          </Card>

          <Card 
            className="cursor-pointer hover:shadow-xl transition-all active:scale-[0.98]"
            onClick={() => setScreen('extract_books')}
            data-testid="card-unload-books"
          >
            <CardContent className="p-7 flex flex-col items-center text-center">
              <Package className="w-14 h-14 text-orange-500 mb-3" />
              <h3 className="text-xl font-bold mb-1">Изъять книги</h3>
              <p className="text-slate-500">Забрать возвращённые</p>
            </CardContent>
          </Card>

          <Card 
            className="cursor-pointer hover:shadow-xl transition-all active:scale-[0.98]"
            onClick={() => {
              setProgressMessage('Инвентаризация...');
              setProgressValue(10);
              setScreen('progress');
              inventoryMutation.mutate();
            }}
            data-testid="card-inventory"
          >
            <CardContent className="p-7 flex flex-col items-center text-center">
              <Search className="w-14 h-14 text-green-500 mb-3" />
              <h3 className="text-xl font-bold mb-1">Инвентаризация</h3>
              <p className="text-slate-500">Проверить содержимое</p>
            </CardContent>
          </Card>

          <Card 
            className="cursor-pointer hover:shadow-xl transition-all active:scale-[0.98]"
            onClick={() => setScreen('operations_log')}
            data-testid="card-operations-log"
          >
            <CardContent className="p-7 flex flex-col items-center text-center">
              <History className="w-14 h-14 text-slate-600 mb-3" />
              <h3 className="text-xl font-bold mb-1">Журнал операций</h3>
              <p className="text-slate-500">История выдач и возвратов</p>
            </CardContent>
          </Card>

          <Card 
            className="cursor-pointer hover:shadow-xl transition-all active:scale-[0.98]"
            onClick={() => setScreen('statistics')}
            data-testid="card-statistics"
          >
            <CardContent className="p-7 flex flex-col items-center text-center">
              <BarChart3 className="w-14 h-14 text-indigo-500 mb-3" />
              <h3 className="text-xl font-bold mb-1">Статистика</h3>
              <p className="text-slate-500">Аналитика и отчёты</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );

  const renderAdminMenu = () => (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-admin-menu">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold text-slate-800 mb-6 text-center">Администрирование</h2>
        
        <div className="grid grid-cols-3 gap-5">
          <Card 
            className="cursor-pointer hover:shadow-xl transition-all active:scale-[0.98]"
            onClick={() => setLocation('/admin')}
            data-testid="card-admin-dashboard"
          >
            <CardContent className="p-7 flex flex-col items-center text-center">
              <Settings className="w-14 h-14 text-slate-600 mb-3" />
              <h3 className="text-xl font-bold mb-1">Dashboard</h3>
              <p className="text-slate-500">Статистика и мониторинг</p>
            </CardContent>
          </Card>

          <Card 
            className="cursor-pointer hover:shadow-xl transition-all active:scale-[0.98]"
            onClick={() => setScreen('librarian_menu')}
            data-testid="card-librarian-functions"
          >
            <CardContent className="p-7 flex flex-col items-center text-center">
              <BookOpen className="w-14 h-14 text-blue-500 mb-3" />
              <h3 className="text-xl font-bold mb-1">Функции библиотекаря</h3>
              <p className="text-slate-500">Загрузка, изъятие</p>
            </CardContent>
          </Card>

          <Card 
            className="cursor-pointer hover:shadow-xl transition-all active:scale-[0.98]"
            onClick={() => setScreen('diagnostics')}
            data-testid="card-diagnostics"
          >
            <CardContent className="p-7 flex flex-col items-center text-center">
              <Shield className="w-14 h-14 text-purple-500 mb-3" />
              <h3 className="text-xl font-bold mb-1">Диагностика</h3>
              <p className="text-slate-500">Проверка оборудования</p>
            </CardContent>
          </Card>

          <Card 
            className="cursor-pointer hover:shadow-xl transition-all active:scale-[0.98]"
            onClick={() => setScreen('mechanics_test')}
            data-testid="card-mechanics-test"
          >
            <CardContent className="p-7 flex flex-col items-center text-center">
              <Cog className="w-14 h-14 text-orange-500 mb-3" />
              <h3 className="text-xl font-bold mb-1">Тест механики</h3>
              <p className="text-slate-500">Моторы, сервоприводы, шторки</p>
            </CardContent>
          </Card>

          <Card 
            className="cursor-pointer hover:shadow-xl transition-all active:scale-[0.98]"
            onClick={() => setScreen('calibration')}
            data-testid="card-calibration"
          >
            <CardContent className="p-7 flex flex-col items-center text-center">
              <Target className="w-14 h-14 text-green-500 mb-3" />
              <h3 className="text-xl font-bold mb-1">Калибровка</h3>
              <p className="text-slate-500">Настройка позиций и скоростей</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );

  const renderBookList = () => (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-book-list">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-slate-800 mb-6">Ваши забронированные книги</h2>
        
        {session?.reservedBooks.length === 0 ? (
          <Card className="p-10 text-center">
            <BookOpen className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <p className="text-xl text-slate-500">Нет забронированных книг</p>
          </Card>
        ) : (
          <div className="space-y-4">
            {session?.reservedBooks.map((book) => (
              <Card key={book.id} className="p-5" data-testid={`card-book-${book.rfid}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xl font-bold">{book.title}</h3>
                    <p className="text-base text-slate-500">{book.author}</p>
                  </div>
                  <Button 
                    size="lg" 
                    className="h-14 px-8 text-lg"
                    onClick={() => handleIssueBook(book)}
                    disabled={issueMutation.isPending}
                    data-testid={`button-issue-${book.rfid}`}
                  >
                    <BookOpen className="w-5 h-5 mr-2" />
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

  const renderLoadBooks = () => (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-load-books">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-3xl font-bold text-slate-800 mb-6">Загрузка книги в шкаф</h2>
        
        <Card className="p-6">
          <div className="space-y-5">
            <div>
              <Label htmlFor="rfid" className="text-lg">RFID-метка книги *</Label>
              <Input 
                id="rfid"
                value={newBookRfid}
                onChange={(e) => setNewBookRfid(e.target.value)}
                placeholder="Сканируйте или введите RFID"
                className="h-14 text-lg mt-2"
                data-testid="input-book-rfid"
              />
            </div>
            
            <div>
              <Label htmlFor="title" className="text-lg">Название книги *</Label>
              <Input 
                id="title"
                value={newBookTitle}
                onChange={(e) => setNewBookTitle(e.target.value)}
                placeholder="Введите название"
                className="h-14 text-lg mt-2"
                data-testid="input-book-title"
              />
            </div>
            
            <div>
              <Label htmlFor="author" className="text-lg">Автор</Label>
              <Input 
                id="author"
                value={newBookAuthor}
                onChange={(e) => setNewBookAuthor(e.target.value)}
                placeholder="Введите автора (необязательно)"
                className="h-14 text-lg mt-2"
                data-testid="input-book-author"
              />
            </div>
            
            <Button 
              size="lg" 
              className="w-full h-16 text-xl"
              onClick={handleLoadBook}
              disabled={loadBookMutation.isPending || !newBookRfid || !newBookTitle}
              data-testid="button-load-book"
            >
              {loadBookMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : <Plus className="w-5 h-5 mr-2" />}
              Загрузить книгу
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );

  const renderExtractBooks = () => {
    const extractionCells = allCells.filter(c => c.needsExtraction);

    return (
      <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-extract-books">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-slate-800 mb-6">Изъятие книг</h2>
          
          {extractionCells.length === 0 ? (
            <Card className="p-10 text-center">
              <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <p className="text-xl text-slate-500">Нет книг для изъятия</p>
            </Card>
          ) : (
            <>
              <div className="mb-4 flex justify-between items-center">
                <span className="text-lg">{extractionCells.length} книг для изъятия</span>
                <Button
                  onClick={() => {
                    setProgressMessage('Изъятие всех книг...');
                    setScreen('progress');
                    extractAllMutation.mutate();
                  }}
                  disabled={extractAllMutation.isPending}
                  data-testid="button-extract-all-page"
                >
                  Изъять все
                </Button>
              </div>
              
              <ScrollArea className="h-96">
                <div className="space-y-3">
                  {extractionCells.map((cell) => (
                    <Card key={cell.id} className="p-4" data-testid={`card-cell-${cell.id}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-lg font-bold">{cell.bookTitle}</h3>
                          <p className="text-sm text-slate-500">
                            Ячейка: {cell.row} X{cell.x} Y{cell.y}
                          </p>
                        </div>
                        <Button 
                          onClick={() => extractMutation.mutate(cell.id)}
                          disabled={extractMutation.isPending}
                          data-testid={`button-extract-${cell.id}`}
                        >
                          Изъять
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            </>
          )}
        </div>
      </div>
    );
  };

  const renderReturnBook = () => (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-return-book">
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-3xl font-bold text-slate-800 mb-6">Возврат книги</h2>
        
        <Card className="p-10">
          <Package className="w-20 h-20 text-green-500 mx-auto mb-4" />
          <p className="text-xl mb-3">Положите книгу в окно приёма</p>
          <p className="text-base text-slate-500 mb-6">
            Книга будет автоматически распознана по RFID-метке
          </p>
          
          <div className="h-2 bg-slate-200 rounded-full overflow-hidden mb-6">
            <div className="h-full bg-green-500 animate-pulse" style={{ width: '30%' }} />
          </div>
          
          <p className="text-slate-500">Ожидание книги...</p>
        </Card>
      </div>
    </div>
  );

  const renderProgress = () => (
    <div className="min-h-screen bg-slate-100 pt-28 flex items-center justify-center" data-testid="screen-progress">
      <Card className="p-10 w-full max-w-xl text-center">
        <Loader2 className="w-20 h-20 text-blue-500 mx-auto mb-4 animate-spin" />
        <h2 className="text-2xl font-bold mb-3">{progressMessage}</h2>
        <Progress value={progressValue} className="h-3 mb-3" />
        <p className="text-slate-500">Пожалуйста, подождите...</p>
      </Card>
    </div>
  );

  const renderSuccess = () => (
    <div className="min-h-screen bg-green-50 pt-28 flex items-center justify-center" data-testid="screen-success">
      <Card className="p-10 w-full max-w-xl text-center border-green-500 border-2">
        <CheckCircle2 className="w-24 h-24 text-green-500 mx-auto mb-4" />
        <h2 className="text-3xl font-bold text-green-700 mb-3">Успешно!</h2>
        <p className="text-xl text-slate-600 mb-6">{successMessage}</p>
        <Button 
          size="lg" 
          className="h-14 px-10 text-lg"
          onClick={handleBack}
          data-testid="button-continue"
        >
          Продолжить
        </Button>
      </Card>
    </div>
  );

  const renderError = () => (
    <div className="min-h-screen bg-red-50 pt-28 flex items-center justify-center" data-testid="screen-error">
      <Card className="p-10 w-full max-w-xl text-center border-red-500 border-2">
        <XCircle className="w-24 h-24 text-red-500 mx-auto mb-4" />
        <h2 className="text-3xl font-bold text-red-700 mb-3">Ошибка</h2>
        <p className="text-xl text-slate-600 mb-6">{errorMessage}</p>
        <Button 
          size="lg" 
          variant="destructive"
          className="h-14 px-10 text-lg"
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
      <Card className="p-10 w-full max-w-xl text-center border-yellow-500 border-2">
        <AlertTriangle className="w-24 h-24 text-yellow-500 mx-auto mb-4" />
        <h2 className="text-3xl font-bold text-yellow-700 mb-3">Шкаф временно недоступен</h2>
        <p className="text-xl text-slate-600">Ведутся технические работы</p>
      </Card>
    </div>
  );

  const renderOperationsLog = () => (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-operations-log">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-slate-800 mb-6">Журнал операций</h2>
        
        {operations.length === 0 ? (
          <Card className="p-10 text-center">
            <History className="w-16 h-16 text-slate-400 mx-auto mb-4" />
            <p className="text-xl text-slate-500">Нет операций</p>
          </Card>
        ) : (
          <ScrollArea className="h-[calc(100vh-200px)]">
            <div className="space-y-3">
              {operations.map((op) => (
                <Card key={op.id} className="p-4" data-testid={`card-operation-${op.id}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge variant={op.result === 'OK' ? 'default' : 'destructive'}>
                          {op.operation}
                        </Badge>
                        <span className="text-sm text-slate-500">
                          {op.timestamp ? new Date(op.timestamp).toLocaleString() : '-'}
                        </span>
                      </div>
                      {op.bookRfid && (
                        <p className="text-slate-600 mt-1">RFID: {op.bookRfid}</p>
                      )}
                    </div>
                    <div className={`text-sm ${op.result === 'OK' ? 'text-green-600' : 'text-red-600'}`}>
                      {op.result === 'OK' ? 'Успешно' : op.result}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );

  const renderStatistics = () => (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-statistics">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-slate-800 mb-6">Статистика</h2>
        
        <div className="grid grid-cols-2 gap-5">
          <Card className="p-6">
            <div className="flex items-center gap-4">
              <BookOpen className="w-12 h-12 text-blue-500" />
              <div>
                <p className="text-sm text-slate-500">Выдано сегодня</p>
                <p className="text-3xl font-bold">{statistics?.issuesToday || 0}</p>
                <p className="text-sm text-slate-400">Всего: {statistics?.issuesTotal || 0}</p>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center gap-4">
              <Undo2 className="w-12 h-12 text-green-500" />
              <div>
                <p className="text-sm text-slate-500">Возвращено сегодня</p>
                <p className="text-3xl font-bold">{statistics?.returnsToday || 0}</p>
                <p className="text-sm text-slate-400">Всего: {statistics?.returnsTotal || 0}</p>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center gap-4">
              <Package className="w-12 h-12 text-slate-500" />
              <div>
                <p className="text-sm text-slate-500">Заполненность шкафа</p>
                <p className="text-3xl font-bold">{statistics?.occupiedCells || 0}/{statistics?.totalCells || 0}</p>
                <Progress 
                  value={statistics?.totalCells ? (statistics.occupiedCells / statistics.totalCells) * 100 : 0} 
                  className="h-2 mt-2 w-32" 
                />
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center gap-4">
              <AlertTriangle className="w-12 h-12 text-orange-500" />
              <div>
                <p className="text-sm text-slate-500">Требуют изъятия</p>
                <p className="text-3xl font-bold text-orange-500">{statistics?.booksNeedExtraction || 0}</p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );

  const renderDiagnostics = () => (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-diagnostics">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-slate-800 mb-6">Диагностика оборудования</h2>
        
        <div className="grid grid-cols-2 gap-5">
          <Card className="p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Датчики
            </h3>
            <div className="space-y-2">
              {diagnostics?.sensors && Object.entries(diagnostics.sensors).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between py-2 border-b">
                  <span className="text-slate-600">{key}</span>
                  <Badge variant={value ? 'default' : 'secondary'}>
                    {value ? 'Активен' : 'Неактивен'}
                  </Badge>
                </div>
              ))}
              {!diagnostics && <p className="text-slate-400">Загрузка...</p>}
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Моторы
            </h3>
            <div className="flex items-center gap-3">
              <div className={`w-4 h-4 rounded-full ${diagnostics?.motors === 'ok' ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-lg">
                {diagnostics?.motors === 'ok' ? 'В норме' : diagnostics?.motors || 'Проверка...'}
              </span>
            </div>
          </Card>

          <Card className="p-6 col-span-2">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <CreditCard className="w-5 h-5" />
              RFID считыватели
            </h3>
            <div className="grid grid-cols-2 gap-4">
              {diagnostics?.rfid && Object.entries(diagnostics.rfid).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between py-2 px-4 bg-slate-50 rounded">
                  <span className="text-slate-600">{key}</span>
                  <Badge variant={value === 'connected' ? 'default' : 'destructive'}>
                    {value === 'connected' ? 'Подключён' : value}
                  </Badge>
                </div>
              ))}
              {!diagnostics && <p className="text-slate-400">Загрузка...</p>}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );

  const renderMechanicsTest = () => (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-mechanics-test">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold text-slate-800 mb-6">Тестирование механики</h2>
        
        <div className="grid grid-cols-2 gap-5">
          <Card className="p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Move className="w-5 h-5" />
              Управление моторами XY
            </h3>
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-2">
                <div />
                <Button 
                  className="h-14"
                  onClick={() => testMotorMutation.mutate({ command: 'move', axis: 'y', steps: -500 })}
                  disabled={testMotorMutation.isPending}
                  data-testid="button-motor-y-minus"
                >
                  <ArrowUp className="w-6 h-6" />
                </Button>
                <div />
                <Button 
                  className="h-14"
                  onClick={() => testMotorMutation.mutate({ command: 'move', axis: 'x', steps: -500 })}
                  disabled={testMotorMutation.isPending}
                  data-testid="button-motor-x-minus"
                >
                  <ArrowLeft className="w-6 h-6" />
                </Button>
                <Button 
                  variant="outline"
                  className="h-14"
                  onClick={() => testMotorMutation.mutate({ command: 'home' })}
                  disabled={testMotorMutation.isPending}
                  data-testid="button-motor-home"
                >
                  <Home className="w-5 h-5" />
                </Button>
                <Button 
                  className="h-14"
                  onClick={() => testMotorMutation.mutate({ command: 'move', axis: 'x', steps: 500 })}
                  disabled={testMotorMutation.isPending}
                  data-testid="button-motor-x-plus"
                >
                  <ArrowRight className="w-6 h-6" />
                </Button>
                <div />
                <Button 
                  className="h-14"
                  onClick={() => testMotorMutation.mutate({ command: 'move', axis: 'y', steps: 500 })}
                  disabled={testMotorMutation.isPending}
                  data-testid="button-motor-y-plus"
                >
                  <ArrowDown className="w-6 h-6" />
                </Button>
                <div />
              </div>
              <div className="text-center text-slate-500">
                Позиция: X={systemStatus?.position?.x || 0}, Y={systemStatus?.position?.y || 0}
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Package className="w-5 h-5" />
              Управление лотком
            </h3>
            <div className="space-y-4">
              <div className="flex gap-3">
                <Button 
                  className="flex-1 h-14"
                  onClick={() => testTrayMutation.mutate('extend')}
                  disabled={testTrayMutation.isPending}
                  data-testid="button-tray-extend"
                >
                  <Play className="w-5 h-5 mr-2" />
                  Выдвинуть
                </Button>
                <Button 
                  variant="outline"
                  className="flex-1 h-14"
                  onClick={() => testTrayMutation.mutate('retract')}
                  disabled={testTrayMutation.isPending}
                  data-testid="button-tray-retract"
                >
                  <RotateCcw className="w-5 h-5 mr-2" />
                  Задвинуть
                </Button>
              </div>
              <div className="text-center text-slate-500">
                Лоток: {systemStatus?.position?.tray || 0} шагов
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Lock className="w-5 h-5" />
              Замки (сервоприводы)
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Передний замок</span>
                <div className="flex gap-2">
                  <Button 
                    size="sm"
                    onClick={() => testServoMutation.mutate({ servo: 'front', command: 'open' })}
                    disabled={testServoMutation.isPending}
                    data-testid="button-lock-front-open"
                  >
                    <Unlock className="w-4 h-4 mr-1" /> Открыть
                  </Button>
                  <Button 
                    size="sm"
                    variant="outline"
                    onClick={() => testServoMutation.mutate({ servo: 'front', command: 'close' })}
                    disabled={testServoMutation.isPending}
                    data-testid="button-lock-front-close"
                  >
                    <Lock className="w-4 h-4 mr-1" /> Закрыть
                  </Button>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-medium">Задний замок</span>
                <div className="flex gap-2">
                  <Button 
                    size="sm"
                    onClick={() => testServoMutation.mutate({ servo: 'back', command: 'open' })}
                    disabled={testServoMutation.isPending}
                    data-testid="button-lock-back-open"
                  >
                    <Unlock className="w-4 h-4 mr-1" /> Открыть
                  </Button>
                  <Button 
                    size="sm"
                    variant="outline"
                    onClick={() => testServoMutation.mutate({ servo: 'back', command: 'close' })}
                    disabled={testServoMutation.isPending}
                    data-testid="button-lock-back-close"
                  >
                    <Lock className="w-4 h-4 mr-1" /> Закрыть
                  </Button>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Шторки
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Внутренняя</span>
                <div className="flex gap-2">
                  <Button 
                    size="sm"
                    onClick={() => testShutterMutation.mutate({ shutter: 'inner', command: 'open' })}
                    disabled={testShutterMutation.isPending}
                    data-testid="button-shutter-inner-open"
                  >
                    Открыть
                  </Button>
                  <Button 
                    size="sm"
                    variant="outline"
                    onClick={() => testShutterMutation.mutate({ shutter: 'inner', command: 'close' })}
                    disabled={testShutterMutation.isPending}
                    data-testid="button-shutter-inner-close"
                  >
                    Закрыть
                  </Button>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-medium">Внешняя</span>
                <div className="flex gap-2">
                  <Button 
                    size="sm"
                    onClick={() => testShutterMutation.mutate({ shutter: 'outer', command: 'open' })}
                    disabled={testShutterMutation.isPending}
                    data-testid="button-shutter-outer-open"
                  >
                    Открыть
                  </Button>
                  <Button 
                    size="sm"
                    variant="outline"
                    onClick={() => testShutterMutation.mutate({ shutter: 'outer', command: 'close' })}
                    disabled={testShutterMutation.isPending}
                    data-testid="button-shutter-outer-close"
                  >
                    Закрыть
                  </Button>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6 col-span-2">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Состояние датчиков
            </h3>
            <div className="grid grid-cols-6 gap-3">
              {diagnostics?.sensors && Object.entries(diagnostics.sensors).map(([key, value]) => (
                <div key={key} className="flex flex-col items-center p-3 bg-slate-50 rounded">
                  <div className={`w-4 h-4 rounded-full mb-2 ${value ? 'bg-green-500' : 'bg-slate-300'}`} />
                  <span className="text-xs text-slate-600">{key}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );

  const renderCalibration = () => (
    <div className="min-h-screen bg-slate-100 pt-28 p-6" data-testid="screen-calibration">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-3xl font-bold text-slate-800">Калибровка</h2>
          <Button 
            variant="destructive"
            onClick={() => resetCalibrationMutation.mutate()}
            disabled={resetCalibrationMutation.isPending}
            data-testid="button-reset-calibration"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Сброс к заводским
          </Button>
        </div>
        
        <div className="grid grid-cols-2 gap-5">
          <Card className="p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Cog className="w-5 h-5" />
              Скорости
            </h3>
            <div className="space-y-4">
              <div>
                <Label>Скорость XY (шаг/сек)</Label>
                <div className="flex gap-2 mt-1">
                  <Input 
                    type="number"
                    value={calibration?.speeds?.xy || 3000}
                    className="h-12"
                    data-testid="input-speed-xy"
                    onChange={(e) => saveCalibrationMutation.mutate({ speeds: { ...calibration?.speeds, xy: parseInt(e.target.value) || 3000 } } as any)}
                  />
                </div>
              </div>
              <div>
                <Label>Скорость лотка (шаг/сек)</Label>
                <div className="flex gap-2 mt-1">
                  <Input 
                    type="number"
                    value={calibration?.speeds?.tray || 2000}
                    className="h-12"
                    data-testid="input-speed-tray"
                    onChange={(e) => saveCalibrationMutation.mutate({ speeds: { ...calibration?.speeds, tray: parseInt(e.target.value) || 2000 } } as any)}
                  />
                </div>
              </div>
              <div>
                <Label>Ускорение (шаг/сек²)</Label>
                <div className="flex gap-2 mt-1">
                  <Input 
                    type="number"
                    value={calibration?.speeds?.acceleration || 5000}
                    className="h-12"
                    data-testid="input-acceleration"
                    onChange={(e) => saveCalibrationMutation.mutate({ speeds: { ...calibration?.speeds, acceleration: parseInt(e.target.value) || 5000 } } as any)}
                  />
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Lock className="w-5 h-5" />
              Углы сервоприводов
            </h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Замок 1 открыт (°)</Label>
                  <Input 
                    type="number"
                    value={calibration?.servos?.lock1_open || 90}
                    className="h-12 mt-1"
                    data-testid="input-servo-lock1-open"
                    onChange={(e) => saveCalibrationMutation.mutate({ servos: { ...calibration?.servos, lock1_open: parseInt(e.target.value) || 90 } } as any)}
                  />
                </div>
                <div>
                  <Label>Замок 1 закрыт (°)</Label>
                  <Input 
                    type="number"
                    value={calibration?.servos?.lock1_close || 0}
                    className="h-12 mt-1"
                    data-testid="input-servo-lock1-close"
                    onChange={(e) => saveCalibrationMutation.mutate({ servos: { ...calibration?.servos, lock1_close: parseInt(e.target.value) || 0 } } as any)}
                  />
                </div>
                <div>
                  <Label>Замок 2 открыт (°)</Label>
                  <Input 
                    type="number"
                    value={calibration?.servos?.lock2_open || 90}
                    className="h-12 mt-1"
                    data-testid="input-servo-lock2-open"
                    onChange={(e) => saveCalibrationMutation.mutate({ servos: { ...calibration?.servos, lock2_open: parseInt(e.target.value) || 90 } } as any)}
                  />
                </div>
                <div>
                  <Label>Замок 2 закрыт (°)</Label>
                  <Input 
                    type="number"
                    value={calibration?.servos?.lock2_close || 0}
                    className="h-12 mt-1"
                    data-testid="input-servo-lock2-close"
                    onChange={(e) => saveCalibrationMutation.mutate({ servos: { ...calibration?.servos, lock2_close: parseInt(e.target.value) || 0 } } as any)}
                  />
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Target className="w-5 h-5" />
              Позиция окна выдачи
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>X (шаги)</Label>
                <Input 
                  type="number"
                  value={calibration?.window?.x || 5000}
                  className="h-12 mt-1"
                  data-testid="input-window-x"
                  onChange={(e) => saveCalibrationMutation.mutate({ window: { ...calibration?.window, x: parseInt(e.target.value) || 5000 } } as any)}
                />
              </div>
              <div>
                <Label>Y (шаги)</Label>
                <Input 
                  type="number"
                  value={calibration?.window?.y || 5000}
                  className="h-12 mt-1"
                  data-testid="input-window-y"
                  onChange={(e) => saveCalibrationMutation.mutate({ window: { ...calibration?.window, y: parseInt(e.target.value) || 5000 } } as any)}
                />
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Move className="w-5 h-5" />
              Кинематика CoreXY
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>X+ dir A</Label>
                <Input 
                  type="number"
                  value={calibration?.kinematics?.x_plus_dir_a || 1}
                  className="h-12 mt-1"
                  data-testid="input-kinematics-x-plus-dir-a"
                  onChange={(e) => saveCalibrationMutation.mutate({ kinematics: { ...calibration?.kinematics, x_plus_dir_a: parseInt(e.target.value) || 1 } } as any)}
                />
              </div>
              <div>
                <Label>X+ dir B</Label>
                <Input 
                  type="number"
                  value={calibration?.kinematics?.x_plus_dir_b || -1}
                  className="h-12 mt-1"
                  data-testid="input-kinematics-x-plus-dir-b"
                  onChange={(e) => saveCalibrationMutation.mutate({ kinematics: { ...calibration?.kinematics, x_plus_dir_b: parseInt(e.target.value) || -1 } } as any)}
                />
              </div>
              <div>
                <Label>Y+ dir A</Label>
                <Input 
                  type="number"
                  value={calibration?.kinematics?.y_plus_dir_a || 1}
                  className="h-12 mt-1"
                  data-testid="input-kinematics-y-plus-dir-a"
                  onChange={(e) => saveCalibrationMutation.mutate({ kinematics: { ...calibration?.kinematics, y_plus_dir_a: parseInt(e.target.value) || 1 } } as any)}
                />
              </div>
              <div>
                <Label>Y+ dir B</Label>
                <Input 
                  type="number"
                  value={calibration?.kinematics?.y_plus_dir_b || 1}
                  className="h-12 mt-1"
                  data-testid="input-kinematics-y-plus-dir-b"
                  onChange={(e) => saveCalibrationMutation.mutate({ kinematics: { ...calibration?.kinematics, y_plus_dir_b: parseInt(e.target.value) || 1 } } as any)}
                />
              </div>
            </div>
          </Card>
        </div>
      </div>
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
      {screen === 'load_books' && renderLoadBooks()}
      {screen === 'extract_books' && renderExtractBooks()}
      {screen === 'operations_log' && renderOperationsLog()}
      {screen === 'statistics' && renderStatistics()}
      {screen === 'diagnostics' && renderDiagnostics()}
      {screen === 'mechanics_test' && renderMechanicsTest()}
      {screen === 'calibration' && renderCalibration()}
      {screen === 'progress' && renderProgress()}
      {screen === 'success' && renderSuccess()}
      {screen === 'error' && renderError()}
      {screen === 'maintenance' && renderMaintenance()}
    </>
  );
}
