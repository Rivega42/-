import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import type { CalibrationData, SystemStatus } from "@shared/schema";
import {
  Settings,
  Play,
  Square,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  RotateCcw,
  Check,
  X,
  Download,
  Upload,
  RefreshCw,
  Crosshair,
  Grid3X3,
  Lock,
  Unlock,
  Zap,
  Save,
  ChevronRight,
  ChevronLeft,
  Home,
  Move,
  Target,
  AlertTriangle,
} from "lucide-react";

type WizardMode = 'menu' | 'kinematics' | 'points10' | 'grab' | 'blocked' | 'quicktest';

interface WizardState {
  mode: WizardMode;
  step: number;
  totalSteps: number;
  instruction: string;
  stepSize: number;
  stepIndex: number;
}

const STEP_SIZES = [1, 2, 5, 10, 15, 20, 30, 50, 100];

export default function CalibrationWizard() {
  const { toast } = useToast();
  const [wizardState, setWizardState] = useState<WizardState>({
    mode: 'menu',
    step: 0,
    totalSteps: 0,
    instruction: '',
    stepSize: 10,
    stepIndex: 3,
  });
  const [isRunning, setIsRunning] = useState(false);
  const [kinematicsStep, setKinematicsStep] = useState<{
    motor: string;
    direction: string;
    label: string;
  } | null>(null);
  const [grabSide, setGrabSide] = useState<'front' | 'back'>('front');
  const [blockedSide, setBlockedSide] = useState<'front' | 'back'>('front');
  const [quickTestCell, setQuickTestCell] = useState({ side: 'front' as 'front' | 'back', col: 0, row: 0 });

  const { data: calibration, refetch: refetchCalibration } = useQuery<CalibrationData>({
    queryKey: ['/api/calibration'],
  });

  const { data: status } = useQuery<SystemStatus>({
    queryKey: ['/api/status'],
    refetchInterval: 1000,
  });

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (wizardState.mode === 'menu') return;
    
    const key = e.key.toUpperCase();
    
    if (['W', 'A', 'S', 'D'].includes(key) && wizardState.mode === 'points10') {
      e.preventDefault();
      moveCarriage(key);
    }
    
    if (key >= '1' && key <= '9') {
      e.preventDefault();
      const idx = parseInt(key) - 1;
      setWizardState(prev => ({ ...prev, stepIndex: idx, stepSize: STEP_SIZES[idx] }));
    }
    
    if (key === 'ENTER' && wizardState.mode === 'points10') {
      e.preventDefault();
      savePoint();
    }
    
    if (key === 'ESCAPE' || key === 'Q') {
      e.preventDefault();
      exitWizard();
    }
  }, [wizardState.mode]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const moveCarriage = async (direction: string) => {
    try {
      const res = await apiRequest('POST', '/api/calibration/wizard/move', {
        direction,
        stepIndex: wizardState.stepIndex,
      });
      const data = await res.json();
      if (data.success) {
        queryClient.invalidateQueries({ queryKey: ['/api/status'] });
      }
    } catch (error) {
      toast({ title: 'Ошибка', description: 'Не удалось выполнить движение', variant: 'destructive' });
    }
  };

  const startKinematics = async () => {
    try {
      setIsRunning(true);
      const res = await apiRequest('POST', '/api/calibration/wizard/kinematics/start', {});
      const data = await res.json();
      if (data.success) {
        setWizardState({
          mode: 'kinematics',
          step: 0,
          totalSteps: 4,
          instruction: data.instruction,
          stepSize: 10,
          stepIndex: 3,
        });
      }
    } catch (error) {
      toast({ title: 'Ошибка', description: 'Не удалось запустить тест кинематики', variant: 'destructive' });
    } finally {
      setIsRunning(false);
    }
  };

  const runKinematicsStep = async () => {
    try {
      setIsRunning(true);
      const res = await apiRequest('POST', '/api/calibration/wizard/kinematics/step', { action: 'run' });
      const data = await res.json();
      if (data.success) {
        setKinematicsStep({ motor: data.motor, direction: data.direction, label: data.label });
        setWizardState(prev => ({ ...prev, instruction: data.instruction }));
      }
    } catch (error) {
      toast({ title: 'Ошибка', variant: 'destructive' });
    } finally {
      setIsRunning(false);
    }
  };

  const respondKinematics = async (response: string) => {
    try {
      setIsRunning(true);
      const res = await apiRequest('POST', '/api/calibration/wizard/kinematics/step', { 
        action: 'response', 
        response 
      });
      const data = await res.json();
      if (data.success) {
        if (data.completed) {
          toast({ title: 'Успех', description: data.message });
          refetchCalibration();
          setWizardState(prev => ({ ...prev, mode: 'menu' }));
          setKinematicsStep(null);
        } else {
          setWizardState(prev => ({ ...prev, step: data.step, instruction: data.instruction }));
          setKinematicsStep(null);
        }
      }
    } catch (error) {
      toast({ title: 'Ошибка', variant: 'destructive' });
    } finally {
      setIsRunning(false);
    }
  };

  const startPoints10 = async () => {
    try {
      setIsRunning(true);
      const res = await apiRequest('POST', '/api/calibration/wizard/points10/start', {});
      const data = await res.json();
      if (data.success) {
        setWizardState({
          mode: 'points10',
          step: 0,
          totalSteps: 10,
          instruction: data.instruction,
          stepSize: data.stepSize,
          stepIndex: 3,
        });
      }
    } catch (error) {
      toast({ title: 'Ошибка', description: 'Не удалось запустить калибровку точек', variant: 'destructive' });
    } finally {
      setIsRunning(false);
    }
  };

  const savePoint = async () => {
    try {
      setIsRunning(true);
      const res = await apiRequest('POST', '/api/calibration/wizard/points10/save', {});
      const data = await res.json();
      if (data.success) {
        if (data.completed) {
          toast({ title: 'Успех', description: data.message });
          refetchCalibration();
          setWizardState(prev => ({ ...prev, mode: 'menu' }));
        } else {
          setWizardState(prev => ({ 
            ...prev, 
            step: data.step, 
            instruction: data.instruction 
          }));
        }
      }
    } catch (error) {
      toast({ title: 'Ошибка', variant: 'destructive' });
    } finally {
      setIsRunning(false);
    }
  };

  const startGrab = async (side: 'front' | 'back') => {
    try {
      setGrabSide(side);
      const res = await apiRequest('POST', '/api/calibration/wizard/grab/start', { side });
      const data = await res.json();
      if (data.success) {
        setWizardState({
          mode: 'grab',
          step: 0,
          totalSteps: 3,
          instruction: data.instruction,
          stepSize: 10,
          stepIndex: 3,
        });
      }
    } catch (error) {
      toast({ title: 'Ошибка', variant: 'destructive' });
    }
  };

  const adjustGrab = async (param: string, delta: number) => {
    try {
      await apiRequest('POST', '/api/calibration/wizard/grab/adjust', { 
        side: grabSide, 
        param, 
        delta 
      });
      refetchCalibration();
    } catch (error) {
      toast({ title: 'Ошибка', variant: 'destructive' });
    }
  };

  const testGrab = async (param: string) => {
    try {
      setIsRunning(true);
      const res = await apiRequest('POST', '/api/calibration/wizard/grab/test', { 
        side: grabSide, 
        param 
      });
      const data = await res.json();
      if (data.success) {
        toast({ title: 'Тест выполнен', description: data.message });
      }
    } catch (error) {
      toast({ title: 'Ошибка', variant: 'destructive' });
    } finally {
      setIsRunning(false);
    }
  };

  const toggleBlockedCell = async (side: 'front' | 'back', col: number, row: number) => {
    const currentBlocked = calibration?.blocked_cells?.[side]?.[String(col)] || [];
    const isBlocked = currentBlocked.includes(row);
    
    try {
      await apiRequest('POST', '/api/calibration/blocked-cells', {
        side,
        column: col,
        rows: [row],
        action: isBlocked ? 'unblock' : 'block',
      });
      refetchCalibration();
    } catch (error) {
      toast({ title: 'Ошибка', variant: 'destructive' });
    }
  };

  const runQuickTest = async () => {
    try {
      setIsRunning(true);
      const res = await apiRequest('POST', '/api/calibration/quick-test', quickTestCell);
      const data = await res.json();
      if (data.success) {
        toast({ title: 'Тест пройден', description: data.message });
      }
    } catch (error) {
      toast({ title: 'Ошибка', variant: 'destructive' });
    } finally {
      setIsRunning(false);
    }
  };

  const exportCalibration = async () => {
    try {
      const res = await apiRequest('GET', '/api/calibration/export', undefined);
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `calibration_${new Date().toISOString().slice(0,10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast({ title: 'Экспорт', description: 'Калибровка экспортирована' });
    } catch (error) {
      toast({ title: 'Ошибка', variant: 'destructive' });
    }
  };

  const resetCalibration = async () => {
    if (!confirm('Сбросить калибровку к значениям по умолчанию?')) return;
    try {
      await apiRequest('POST', '/api/calibration/reset', {});
      refetchCalibration();
      toast({ title: 'Сброс', description: 'Калибровка сброшена' });
    } catch (error) {
      toast({ title: 'Ошибка', variant: 'destructive' });
    }
  };

  const exitWizard = async () => {
    await apiRequest('POST', '/api/calibration/wizard/exit', {});
    setWizardState(prev => ({ ...prev, mode: 'menu' }));
    setKinematicsStep(null);
  };

  const renderMenu = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <Card className="cursor-pointer hover:border-blue-500 transition-colors" onClick={startKinematics} data-testid="btn-cal-kinematics">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <RotateCcw className="w-5 h-5 text-blue-500" />
              K - Тест кинематики
            </CardTitle>
            <CardDescription>Определение направлений моторов CoreXY</CardDescription>
          </CardHeader>
          <CardContent>
            <Badge variant="outline">4 шага • 2-3 мин</Badge>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:border-blue-500 transition-colors" onClick={startPoints10} data-testid="btn-cal-points">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Crosshair className="w-5 h-5 text-green-500" />
              C - Калибровка 10 точек
            </CardTitle>
            <CardDescription>Калибровка X[0-2] и Y[0,1,5,10,15,20]</CardDescription>
          </CardHeader>
          <CardContent>
            <Badge variant="outline">10 шагов • 10-15 мин</Badge>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:border-blue-500 transition-colors" onClick={() => startGrab('front')} data-testid="btn-cal-grab-front">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Move className="w-5 h-5 text-orange-500" />
              L - Захват FRONT
            </CardTitle>
            <CardDescription>Настройка extend1, retract, extend2</CardDescription>
          </CardHeader>
          <CardContent>
            <Badge variant="outline">3 параметра • 5 мин</Badge>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:border-blue-500 transition-colors" onClick={() => startGrab('back')} data-testid="btn-cal-grab-back">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Move className="w-5 h-5 text-purple-500" />
              L - Захват BACK
            </CardTitle>
            <CardDescription>Настройка extend1, retract, extend2</CardDescription>
          </CardHeader>
          <CardContent>
            <Badge variant="outline">3 параметра • 5 мин</Badge>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:border-blue-500 transition-colors" onClick={() => setWizardState(prev => ({ ...prev, mode: 'blocked' }))} data-testid="btn-cal-blocked">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Grid3X3 className="w-5 h-5 text-red-500" />
              # - Заблокированные ячейки
            </CardTitle>
            <CardDescription>Редактор недоступных ячеек</CardDescription>
          </CardHeader>
          <CardContent>
            <Badge variant="outline">Визуальный редактор</Badge>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:border-blue-500 transition-colors" onClick={() => setWizardState(prev => ({ ...prev, mode: 'quicktest' }))} data-testid="btn-cal-quicktest">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Zap className="w-5 h-5 text-yellow-500" />
              X - Быстрый тест
            </CardTitle>
            <CardDescription>Проверка отдельной ячейки</CardDescription>
          </CardHeader>
          <CardContent>
            <Badge variant="outline">Выбор ячейки</Badge>
          </CardContent>
        </Card>
      </div>

      <Separator />

      <div className="flex gap-2">
        <Button variant="outline" onClick={exportCalibration} data-testid="btn-export-cal">
          <Download className="w-4 h-4 mr-2" />
          Экспорт
        </Button>
        <Button variant="outline" onClick={resetCalibration} data-testid="btn-reset-cal">
          <RefreshCw className="w-4 h-4 mr-2" />
          Сброс
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Текущая калибровка</CardTitle>
        </CardHeader>
        <CardContent className="text-xs font-mono space-y-1">
          <div>Версия: {calibration?.version} | {calibration?.timestamp?.slice(0, 19)}</div>
          <div>Kinematics: A({calibration?.kinematics.x_plus_dir_a}, {calibration?.kinematics.y_plus_dir_a}) B({calibration?.kinematics.x_plus_dir_b}, {calibration?.kinematics.y_plus_dir_b})</div>
          <div>X: [{calibration?.positions.x.join(', ')}]</div>
          <div>Y: [{calibration?.positions.y.slice(0, 5).join(', ')}...{calibration?.positions.y.slice(-2).join(', ')}]</div>
        </CardContent>
      </Card>
    </div>
  );

  const renderKinematics = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Тест кинематики CoreXY</h3>
        <Button variant="outline" size="sm" onClick={exitWizard}>
          <X className="w-4 h-4 mr-1" /> Выход
        </Button>
      </div>

      <Progress value={(wizardState.step / wizardState.totalSteps) * 100} />
      <p className="text-sm text-muted-foreground">Шаг {wizardState.step + 1} из {wizardState.totalSteps}</p>

      <Card className="bg-slate-50">
        <CardContent className="p-6 text-center">
          {kinematicsStep ? (
            <div className="space-y-6">
              <div className="text-2xl font-bold">{kinematicsStep.label}</div>
              <p className="text-lg text-slate-600">Куда поехала каретка?</p>
              
              <div className="grid grid-cols-2 gap-4 max-w-[400px] mx-auto">
                <Button 
                  size="lg" 
                  className="h-20 text-lg flex flex-col gap-1"
                  onClick={() => respondKinematics('W')} 
                  disabled={isRunning} 
                  data-testid="btn-kin-w"
                >
                  <ArrowUp className="w-6 h-6" />
                  <span>Вверх (Y+)</span>
                </Button>
                <Button 
                  size="lg" 
                  className="h-20 text-lg flex flex-col gap-1"
                  onClick={() => respondKinematics('S')} 
                  disabled={isRunning} 
                  data-testid="btn-kin-s"
                >
                  <ArrowDown className="w-6 h-6" />
                  <span>Вниз (Y−)</span>
                </Button>
                <Button 
                  size="lg" 
                  className="h-20 text-lg flex flex-col gap-1"
                  onClick={() => respondKinematics('A')} 
                  disabled={isRunning} 
                  data-testid="btn-kin-a"
                >
                  <ArrowLeft className="w-6 h-6" />
                  <span>Влево (X−)</span>
                </Button>
                <Button 
                  size="lg" 
                  className="h-20 text-lg flex flex-col gap-1"
                  onClick={() => respondKinematics('D')} 
                  disabled={isRunning} 
                  data-testid="btn-kin-d"
                >
                  <ArrowRight className="w-6 h-6" />
                  <span>Вправо (X+)</span>
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-lg">{wizardState.instruction}</p>
              <Button size="lg" onClick={runKinematicsStep} disabled={isRunning} data-testid="btn-kin-run">
                <Play className="w-5 h-5 mr-2" />
                Запустить тест
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );

  const renderPoints10 = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Калибровка 10 ключевых точек</h3>
        <Button variant="outline" size="sm" onClick={exitWizard}>
          <X className="w-4 h-4 mr-1" /> Выход (Q)
        </Button>
      </div>

      <Progress value={(wizardState.step / wizardState.totalSteps) * 100} />
      <p className="text-sm text-muted-foreground">Точка {wizardState.step + 1} из {wizardState.totalSteps}</p>

      <Card>
        <CardContent className="p-4">
          <p className="mb-4">{wizardState.instruction}</p>
          
          <div className="grid grid-cols-2 gap-6">
            <div>
              <div className="grid grid-cols-3 gap-2 max-w-[200px]">
                <div></div>
                <Button variant="outline" onClick={() => moveCarriage('W')} data-testid="btn-move-w">
                  <ArrowUp className="w-6 h-6" />
                </Button>
                <div></div>
                
                <Button variant="outline" onClick={() => moveCarriage('A')} data-testid="btn-move-a">
                  <ArrowLeft className="w-6 h-6" />
                </Button>
                <div className="flex items-center justify-center text-xs text-slate-400">
                  {wizardState.stepSize}мм
                </div>
                <Button variant="outline" onClick={() => moveCarriage('D')} data-testid="btn-move-d">
                  <ArrowRight className="w-6 h-6" />
                </Button>
                
                <div></div>
                <Button variant="outline" onClick={() => moveCarriage('S')} data-testid="btn-move-s">
                  <ArrowDown className="w-6 h-6" />
                </Button>
                <div></div>
              </div>
              
              <div className="mt-4">
                <p className="text-xs text-slate-500 mb-2">Размер шага (1-9):</p>
                <div className="flex flex-wrap gap-1">
                  {STEP_SIZES.map((size, idx) => (
                    <Button
                      key={size}
                      variant={wizardState.stepIndex === idx ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setWizardState(prev => ({ ...prev, stepIndex: idx, stepSize: size }))}
                      data-testid={`btn-step-${idx + 1}`}
                    >
                      {size}
                    </Button>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="text-sm font-mono bg-slate-100 p-3 rounded">
                <div>X: {status?.position.x || 0}</div>
                <div>Y: {status?.position.y || 0}</div>
              </div>
              
              <Button className="w-full" onClick={savePoint} disabled={isRunning} data-testid="btn-save-point">
                <Check className="w-4 h-4 mr-2" />
                Сохранить точку (Enter)
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderGrab = () => {
    const grabData = grabSide === 'front' ? calibration?.grab_front : calibration?.grab_back;
    
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Калибровка захвата {grabSide.toUpperCase()}</h3>
          <Button variant="outline" size="sm" onClick={exitWizard}>
            <X className="w-4 h-4 mr-1" /> Выход
          </Button>
        </div>

        <div className="space-y-4">
          {['extend1', 'retract', 'extend2'].map((param, idx) => (
            <Card key={param}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">
                      {param === 'extend1' ? 'Первое выдвижение (до 1-го пропила)' :
                       param === 'retract' ? 'Втягивание' :
                       'Второе выдвижение (до 2-го пропила)'}
                    </div>
                    <div className="text-2xl font-mono mt-1">
                      {grabData?.[param as keyof typeof grabData] || 0} шагов
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => adjustGrab(param, -100)}>-100</Button>
                    <Button variant="outline" size="sm" onClick={() => adjustGrab(param, -10)}>-10</Button>
                    <Button variant="outline" size="sm" onClick={() => adjustGrab(param, 10)}>+10</Button>
                    <Button variant="outline" size="sm" onClick={() => adjustGrab(param, 100)}>+100</Button>
                    <Button variant="secondary" onClick={() => testGrab(param)} disabled={isRunning}>
                      <Play className="w-4 h-4 mr-1" /> Тест
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Button className="w-full" onClick={() => setWizardState(prev => ({ ...prev, mode: 'menu' }))}>
          <Check className="w-4 h-4 mr-2" />
          Готово
        </Button>
      </div>
    );
  };

  const renderBlocked = () => (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Редактор заблокированных ячеек</h3>
          <Button variant="outline" size="sm" onClick={() => setWizardState(prev => ({ ...prev, mode: 'menu' }))}>
            <X className="w-4 h-4 mr-1" /> Закрыть
          </Button>
        </div>

        <Tabs value={blockedSide} onValueChange={(v) => setBlockedSide(v as 'front' | 'back')}>
          <TabsList>
            <TabsTrigger value="front">FRONT (к читателю)</TabsTrigger>
            <TabsTrigger value="back">BACK (к библиотекарю)</TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="flex gap-2 text-sm">
          <Badge variant="outline" className="flex items-center gap-1">
            <div className="w-3 h-3 bg-green-500 rounded"></div> Доступна
          </Badge>
          <Badge variant="outline" className="flex items-center gap-1">
            <div className="w-3 h-3 bg-red-500 rounded"></div> Заблокирована
          </Badge>
        </div>

        <ScrollArea className="h-[400px]">
          <div className="grid grid-cols-3 gap-1">
            {[0, 1, 2].map(col => (
              <div key={col} className="space-y-1">
                <div className="text-center text-xs font-medium text-slate-500 mb-2">
                  Колонка {col}
                </div>
                {Array.from({ length: 21 }, (_, row) => {
                  const blocked = calibration?.blocked_cells?.[blockedSide]?.[String(col)]?.includes(row);
                  return (
                    <Button
                      key={row}
                      variant="outline"
                      size="sm"
                      className={`w-full h-10 font-medium ${blocked 
                        ? 'bg-red-200 border-red-400 hover:bg-red-300 text-red-800' 
                        : 'bg-green-200 border-green-400 hover:bg-green-300 text-green-800'}`}
                      onClick={() => toggleBlockedCell(blockedSide, col, row)}
                      data-testid={`btn-cell-${blockedSide}-${col}-${row}`}
                    >
                      <span className="text-sm flex items-center">
                        {blocked ? <Lock className="w-4 h-4 mr-1" /> : <Unlock className="w-4 h-4 mr-1" />}
                        Y{row}
                      </span>
                    </Button>
                  );
                })}
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>
  );

  const renderQuickTest = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Быстрый тест ячейки</h3>
        <Button variant="outline" size="sm" onClick={() => setWizardState(prev => ({ ...prev, mode: 'menu' }))}>
          <X className="w-4 h-4 mr-1" /> Закрыть
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="text-sm font-medium">Сторона</label>
          <div className="flex gap-2 mt-1">
            <Button
              variant={quickTestCell.side === 'front' ? 'default' : 'outline'}
              onClick={() => setQuickTestCell(prev => ({ ...prev, side: 'front' }))}
            >
              FRONT
            </Button>
            <Button
              variant={quickTestCell.side === 'back' ? 'default' : 'outline'}
              onClick={() => setQuickTestCell(prev => ({ ...prev, side: 'back' }))}
            >
              BACK
            </Button>
          </div>
        </div>

        <div>
          <label className="text-sm font-medium">Колонка (X)</label>
          <div className="flex gap-2 mt-1">
            {[0, 1, 2].map(col => (
              <Button
                key={col}
                variant={quickTestCell.col === col ? 'default' : 'outline'}
                onClick={() => setQuickTestCell(prev => ({ ...prev, col }))}
              >
                {col}
              </Button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-sm font-medium">Ряд (Y)</label>
          <div className="flex flex-wrap gap-1 mt-1">
            {[0, 5, 10, 15, 20].map(row => (
              <Button
                key={row}
                size="sm"
                variant={quickTestCell.row === row ? 'default' : 'outline'}
                onClick={() => setQuickTestCell(prev => ({ ...prev, row }))}
              >
                {row}
              </Button>
            ))}
          </div>
        </div>
      </div>

      <Card className="bg-slate-50">
        <CardContent className="p-6 text-center">
          <div className="text-lg mb-4">
            Тест ячейки: <strong>{quickTestCell.side.toUpperCase()}</strong> ({quickTestCell.col}, {quickTestCell.row})
          </div>
          <div className="text-sm text-slate-500 mb-4">
            Позиция: X={calibration?.positions.x[quickTestCell.col]}, Y={calibration?.positions.y[quickTestCell.row]}
          </div>
          <Button size="lg" onClick={runQuickTest} disabled={isRunning} data-testid="btn-run-quicktest">
            <Play className="w-5 h-5 mr-2" />
            {isRunning ? 'Выполняется...' : 'Запустить тест'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="w-5 h-5" />
          Калибровка системы
        </CardTitle>
        <CardDescription>
          Пошаговая настройка механики шкафа книговыдачи
        </CardDescription>
      </CardHeader>
      <CardContent>
        {wizardState.mode === 'menu' && renderMenu()}
        {wizardState.mode === 'kinematics' && renderKinematics()}
        {wizardState.mode === 'points10' && renderPoints10()}
        {wizardState.mode === 'grab' && renderGrab()}
        {wizardState.mode === 'blocked' && renderBlocked()}
        {wizardState.mode === 'quicktest' && renderQuickTest()}
      </CardContent>
    </Card>
  );
}
