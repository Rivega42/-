import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { apiRequest, queryClient } from "@/lib/queryClient";
import CalibrationWizard from "@/components/CalibrationWizard";
import type { Cell, Book, User, Operation, SystemLog, Statistics, SystemStatus } from "@shared/schema";
import {
  LayoutDashboard,
  Package,
  Users,
  BookOpen,
  History,
  Settings,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ArrowLeft,
  RefreshCw,
  Wifi,
  WifiOff,
  Database,
  Crosshair,
} from "lucide-react";

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState("dashboard");

  const { data: status } = useQuery<SystemStatus>({
    queryKey: ['/api/status'],
    refetchInterval: 2000,
  });

  const { data: statistics } = useQuery<Statistics>({
    queryKey: ['/api/statistics'],
    refetchInterval: 5000,
  });

  const { data: cells = [] } = useQuery<Cell[]>({
    queryKey: ['/api/cells'],
  });

  const { data: books = [] } = useQuery<Book[]>({
    queryKey: ['/api/books'],
  });

  const { data: users = [] } = useQuery<User[]>({
    queryKey: ['/api/users'],
  });

  const { data: operations = [] } = useQuery<Operation[]>({
    queryKey: ['/api/operations'],
  });

  const { data: logs = [] } = useQuery<SystemLog[]>({
    queryKey: ['/api/logs'],
    refetchInterval: 3000,
  });

  const toggleMaintenance = async () => {
    await apiRequest('POST', '/api/maintenance', { enabled: !status?.maintenanceMode });
    queryClient.invalidateQueries({ queryKey: ['/api/status'] });
  };

  const renderDashboard = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <Card data-testid="stat-card-issues">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Выдачи сегодня</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{statistics?.issuesToday || 0}</div>
            <p className="text-xs text-slate-500">Всего: {statistics?.issuesTotal || 0}</p>
          </CardContent>
        </Card>

        <Card data-testid="stat-card-returns">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Возвраты сегодня</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{statistics?.returnsToday || 0}</div>
            <p className="text-xs text-slate-500">Всего: {statistics?.returnsTotal || 0}</p>
          </CardContent>
        </Card>

        <Card data-testid="stat-card-cells">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Заполненность</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {statistics?.occupiedCells || 0}/{statistics?.totalCells || 0}
            </div>
            <p className="text-xs text-slate-500">
              {statistics?.totalCells ? Math.round((statistics.occupiedCells / statistics.totalCells) * 100) : 0}%
            </p>
          </CardContent>
        </Card>

        <Card data-testid="stat-card-extraction">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Требуют изъятия</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-orange-500">{statistics?.booksNeedExtraction || 0}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Состояние системы</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span>Статус</span>
              <Badge variant={status?.state === 'idle' ? 'default' : status?.state === 'error' ? 'destructive' : 'secondary'}>
                {status?.state || 'unknown'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span>ИРБИС64</span>
              {status?.irbisConnected ? (
                <Badge variant="default" className="flex items-center gap-1">
                  <Wifi className="w-3 h-3" /> Подключен
                </Badge>
              ) : (
                <Badge variant="secondary" className="flex items-center gap-1">
                  <WifiOff className="w-3 h-3" /> Автономный режим
                </Badge>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span>Режим обслуживания</span>
              <Switch checked={status?.maintenanceMode} onCheckedChange={toggleMaintenance} data-testid="switch-maintenance" />
            </div>
            <Separator />
            <div className="text-sm text-slate-500">
              Позиция: X={status?.position.x}, Y={status?.position.y}, Tray={status?.position.tray}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Датчики</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {Object.entries(status?.sensors || {}).map(([name, value]) => (
                <div key={name} className="flex items-center justify-between p-2 bg-slate-50 rounded">
                  <span>{name.replace('_', ' ')}</span>
                  {value ? (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  ) : (
                    <XCircle className="w-4 h-4 text-slate-300" />
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Последние события</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-48">
            {logs.slice(0, 10).map((log) => (
              <div key={log.id} className="flex items-center gap-3 py-2 border-b last:border-0">
                {log.level === 'ERROR' && <XCircle className="w-4 h-4 text-red-500" />}
                {log.level === 'WARNING' && <AlertTriangle className="w-4 h-4 text-yellow-500" />}
                {log.level === 'SUCCESS' && <CheckCircle className="w-4 h-4 text-green-500" />}
                {log.level === 'INFO' && <Database className="w-4 h-4 text-blue-500" />}
                <span className="text-sm">{log.message}</span>
                <span className="text-xs text-slate-400 ml-auto">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );

  const renderCabinetMap = () => {
    const frontCells = cells.filter(c => c.row === 'FRONT');
    const backCells = cells.filter(c => c.row === 'BACK');

    const getCellColor = (cell: Cell | undefined) => {
      if (!cell) return 'bg-slate-100';
      switch (cell.status) {
        case 'blocked': return 'bg-slate-300';
        case 'occupied': return 'bg-blue-500';
        case 'reserved': return 'bg-green-500';
        case 'empty': return 'bg-white border-2 border-slate-200';
        default: return 'bg-slate-100';
      }
    };

    const renderRow = (rowCells: Cell[], rowName: string) => (
      <div>
        <h3 className="font-bold mb-2">{rowName}</h3>
        <div className="grid grid-cols-21 gap-1">
          {[0, 1, 2].map(x => (
            <div key={x} className="contents">
              {Array.from({ length: 21 }, (_, y) => {
                const cell = rowCells.find(c => c.x === x && c.y === y);
                return (
                  <div
                    key={`${x}-${y}`}
                    className={`w-6 h-6 rounded text-xs flex items-center justify-center ${getCellColor(cell)}`}
                    title={cell ? `${cell.row} X${cell.x} Y${cell.y}: ${cell.status}${cell.bookTitle ? ` - ${cell.bookTitle}` : ''}` : ''}
                    data-testid={`cell-${rowName}-${x}-${y}`}
                  >
                    {cell?.needsExtraction && '!'}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    );

    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Карта шкафа</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-white border-2 border-slate-200 rounded" />
                <span>Свободна</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-blue-500 rounded" />
                <span>Занята</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-green-500 rounded" />
                <span>Забронирована</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-slate-300 rounded" />
                <span>Заблокирована</span>
              </div>
            </div>
            
            {renderRow(frontCells, 'FRONT')}
            <Separator />
            {renderRow(backCells, 'BACK')}
          </CardContent>
        </Card>
      </div>
    );
  };

  const renderBooks = () => (
    <Card>
      <CardHeader>
        <CardTitle>Книги в системе</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-96">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">RFID</th>
                <th className="text-left py-2">Название</th>
                <th className="text-left py-2">Автор</th>
                <th className="text-left py-2">Статус</th>
                <th className="text-left py-2">Ячейка</th>
              </tr>
            </thead>
            <tbody>
              {books.map((book) => (
                <tr key={book.id} className="border-b" data-testid={`row-book-${book.rfid}`}>
                  <td className="py-2 font-mono text-sm">{book.rfid}</td>
                  <td className="py-2">{book.title}</td>
                  <td className="py-2 text-slate-500">{book.author}</td>
                  <td className="py-2">
                    <Badge variant={
                      book.status === 'issued' ? 'destructive' :
                      book.status === 'reserved' ? 'default' : 'secondary'
                    }>
                      {book.status}
                    </Badge>
                  </td>
                  <td className="py-2">{book.cellId !== null ? `#${book.cellId}` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollArea>
      </CardContent>
    </Card>
  );

  const renderUsers = () => (
    <Card>
      <CardHeader>
        <CardTitle>Пользователи</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-96">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">RFID</th>
                <th className="text-left py-2">Имя</th>
                <th className="text-left py-2">Роль</th>
                <th className="text-left py-2">Email</th>
                <th className="text-left py-2">Статус</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b" data-testid={`row-user-${user.rfid}`}>
                  <td className="py-2 font-mono text-sm">{user.rfid}</td>
                  <td className="py-2">{user.name}</td>
                  <td className="py-2">
                    <Badge variant={
                      user.role === 'admin' ? 'destructive' :
                      user.role === 'librarian' ? 'secondary' : 'default'
                    }>
                      {user.role}
                    </Badge>
                  </td>
                  <td className="py-2 text-slate-500">{user.email || '-'}</td>
                  <td className="py-2">
                    {user.blocked ? (
                      <Badge variant="destructive">Заблокирован</Badge>
                    ) : (
                      <Badge variant="outline">Активен</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollArea>
      </CardContent>
    </Card>
  );

  const renderOperations = () => (
    <Card>
      <CardHeader>
        <CardTitle>История операций</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-96">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">Время</th>
                <th className="text-left py-2">Операция</th>
                <th className="text-left py-2">Ячейка</th>
                <th className="text-left py-2">Книга</th>
                <th className="text-left py-2">Результат</th>
              </tr>
            </thead>
            <tbody>
              {operations.map((op) => (
                <tr key={op.id} className="border-b" data-testid={`row-operation-${op.id}`}>
                  <td className="py-2 text-sm">
                    {op.timestamp ? new Date(op.timestamp).toLocaleString() : '-'}
                  </td>
                  <td className="py-2">
                    <Badge>{op.operation}</Badge>
                  </td>
                  <td className="py-2">
                    {op.cellRow ? `${op.cellRow} X${op.cellX} Y${op.cellY}` : '-'}
                  </td>
                  <td className="py-2 font-mono text-sm">{op.bookRfid || '-'}</td>
                  <td className="py-2">
                    <Badge variant={op.result === 'OK' ? 'default' : 'destructive'}>
                      {op.result}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollArea>
      </CardContent>
    </Card>
  );

  return (
    <div className="min-h-screen bg-slate-100" data-testid="page-admin">
      <div className="bg-slate-900 text-white p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" className="text-white hover:bg-slate-800" data-testid="button-back-home">
                <ArrowLeft className="w-4 h-4 mr-2" />
                На главную
              </Button>
            </Link>
            <Separator orientation="vertical" className="h-6 bg-slate-600" />
            <h1 className="text-xl font-bold">Панель администратора</h1>
          </div>
          <Button variant="outline" className="border-white text-white" onClick={() => {
            queryClient.invalidateQueries();
          }} data-testid="button-refresh">
            <RefreshCw className="w-4 h-4 mr-2" />
            Обновить
          </Button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid grid-cols-7 w-full max-w-4xl mb-6">
            <TabsTrigger value="dashboard" className="flex items-center gap-2" data-testid="tab-dashboard">
              <LayoutDashboard className="w-4 h-4" />
              Dashboard
            </TabsTrigger>
            <TabsTrigger value="cabinet" className="flex items-center gap-2" data-testid="tab-cabinet">
              <Package className="w-4 h-4" />
              Шкаф
            </TabsTrigger>
            <TabsTrigger value="books" className="flex items-center gap-2" data-testid="tab-books">
              <BookOpen className="w-4 h-4" />
              Книги
            </TabsTrigger>
            <TabsTrigger value="users" className="flex items-center gap-2" data-testid="tab-users">
              <Users className="w-4 h-4" />
              Пользователи
            </TabsTrigger>
            <TabsTrigger value="operations" className="flex items-center gap-2" data-testid="tab-operations">
              <History className="w-4 h-4" />
              Операции
            </TabsTrigger>
            <TabsTrigger value="calibration" className="flex items-center gap-2" data-testid="tab-calibration">
              <Crosshair className="w-4 h-4" />
              Калибровка
            </TabsTrigger>
            <TabsTrigger value="settings" className="flex items-center gap-2" data-testid="tab-settings">
              <Settings className="w-4 h-4" />
              Настройки
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard">{renderDashboard()}</TabsContent>
          <TabsContent value="cabinet">{renderCabinetMap()}</TabsContent>
          <TabsContent value="books">{renderBooks()}</TabsContent>
          <TabsContent value="users">{renderUsers()}</TabsContent>
          <TabsContent value="operations">{renderOperations()}</TabsContent>
          <TabsContent value="calibration">
            <CalibrationWizard />
          </TabsContent>
          <TabsContent value="settings">
            <Card>
              <CardHeader>
                <CardTitle>Настройки системы</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-500">Настройки будут доступны в следующей версии</p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
