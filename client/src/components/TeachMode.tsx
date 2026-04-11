import { useState, useEffect, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import {
  Circle, Square, Save, Trash2, Play, ChevronRight, SkipForward,
  Undo2, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Check,
} from "lucide-react";

interface TeachStatus {
  active: boolean;
  name: string;
  stepsCount: number;
  pending: boolean;
}

export default function TeachMode() {
  const [status, setStatus] = useState<TeachStatus>({ active: false, name: '', stepsCount: 0, pending: false });
  const [seqName, setSeqName] = useState('');
  const [jogSteps, setJogSteps] = useState(100);
  const [logs, setLogs] = useState<string[]>([]);
  const [sequences, setSequences] = useState<Record<string, any[]>>({});
  const [moveX, setMoveX] = useState(0);
  const [moveY, setMoveY] = useState(0);
  const logRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  useEffect(() => {
    refreshStatus();
    loadSequences();
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  function log(msg: string) {
    const ts = new Date().toLocaleTimeString();
    setLogs(prev => [...prev.slice(-99), `[${ts}] ${msg}`]);
  }

  async function refreshStatus() {
    try {
      const res = await apiRequest('GET', '/api/teach/status');
      const data = await res.json();
      setStatus(data);
    } catch {}
  }

  async function loadSequences() {
    try {
      const res = await apiRequest('GET', '/api/teach/sequences');
      setSequences(await res.json());
    } catch {}
  }

  async function api(method: string, path: string, body?: any) {
    try {
      const res = await apiRequest(method, path, body);
      const data = await res.json();
      if (data.message) log(data.message);
      await refreshStatus();
      return data;
    } catch (e: any) {
      log(`Ошибка: ${e.message}`);
      toast({ title: 'Ошибка', description: e.message, variant: 'destructive' });
      return null;
    }
  }

  async function startRecording() {
    if (!seqName.trim()) {
      toast({ title: 'Ошибка', description: 'Введите название', variant: 'destructive' });
      return;
    }
    await api('POST', '/api/teach/start', { name: seqName.trim() });
  }

  async function executeAction(action: string, params: any) {
    await api('POST', '/api/teach/execute', { action, params });
  }

  async function executeMoveXY() {
    await api('POST', '/api/teach/execute', { action: 'move_xy', params: { x: moveX, y: moveY } });
  }

  async function jog(axis: string, direction: number) {
    await api('POST', '/api/teach/jog', { axis, steps: jogSteps * direction });
  }

  async function saveSequence() {
    await api('POST', '/api/teach/save', {});
    setSeqName('');
    loadSequences();
  }

  async function playSequence(name: string) {
    if (!confirm(`Воспроизвести "${name}"?`)) return;
    await api('POST', '/api/teach/play', { name });
  }

  const active = status.active;

  return (
    <div className="space-y-5">
      {/* Session Control */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold">Сессия записи</h3>
          <Badge variant={active ? 'destructive' : 'secondary'}>
            {active ? <><Circle className="w-3 h-3 mr-1 fill-current" /> Запись</> : <><Square className="w-3 h-3 mr-1" /> Не активен</>}
          </Badge>
        </div>
        <div className="flex gap-3">
          <Input placeholder="Название последовательности" value={seqName}
            onChange={e => setSeqName(e.target.value)} disabled={active} className="flex-1" />
          <Button variant="destructive" onClick={startRecording} disabled={active}>
            <Circle className="w-4 h-4 mr-1 fill-current" /> Запись
          </Button>
          <Button onClick={saveSequence} disabled={!active}>
            <Save className="w-4 h-4 mr-1" /> Сохранить
          </Button>
          <Button variant="secondary" onClick={() => api('POST', '/api/teach/discard', {})} disabled={!active}>
            <Trash2 className="w-4 h-4 mr-1" /> Отменить
          </Button>
        </div>
      </Card>

      {/* Log */}
      <Card className="p-3">
        <div ref={logRef} className="h-32 overflow-y-auto bg-slate-900 rounded p-2 font-mono text-xs text-green-400">
          {logs.length === 0 ? <span className="text-slate-500">Лог пуст</span> :
            logs.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      </Card>

      {/* Commands */}
      <Card className={`p-5 ${!active ? 'opacity-50' : ''}`}>
        <h3 className="text-lg font-bold mb-3">Команды</h3>
        <div className="flex flex-wrap gap-2 mb-4">
          <Button size="sm" onClick={() => executeAction('open_shutters', {})} disabled={!active}>Открыть шторки</Button>
          <Button size="sm" onClick={() => executeAction('close_shutters', {})} disabled={!active}>Закрыть шторки</Button>
          <Button size="sm" onClick={() => executeAction('extend_tray', { steps: 5000 })} disabled={!active}>Выдвинуть лоток</Button>
          <Button size="sm" onClick={() => executeAction('retract_tray', { steps: 5000 })} disabled={!active}>Убрать лоток</Button>
          <Button size="sm" onClick={() => executeAction('wait', { ms: 2000 })} disabled={!active}>Пауза 2с</Button>
        </div>
        <div className="flex items-center gap-2">
          <Label>X:</Label>
          <Input type="number" className="w-24" value={moveX} onChange={e => setMoveX(parseInt(e.target.value) || 0)} />
          <Label>Y:</Label>
          <Input type="number" className="w-24" value={moveY} onChange={e => setMoveY(parseInt(e.target.value) || 0)} />
          <Button size="sm" onClick={executeMoveXY} disabled={!active}>
            <ChevronRight className="w-4 h-4 mr-1" /> Перейти XY
          </Button>
        </div>
      </Card>

      {/* Jog */}
      <Card className={`p-5 ${!active ? 'opacity-50' : ''}`}>
        <h3 className="text-lg font-bold mb-3">Коррекция (джог)</h3>
        <div className="flex items-center gap-3 mb-3">
          <Label>Шаг:</Label>
          <Input type="number" className="w-24" value={jogSteps}
            onChange={e => setJogSteps(parseInt(e.target.value) || 100)} />
          <Button size="sm" onClick={() => jog('x', 1)} disabled={!active}><ArrowRight className="w-4 h-4 mr-1" /> +X</Button>
          <Button size="sm" onClick={() => jog('x', -1)} disabled={!active}><ArrowLeft className="w-4 h-4 mr-1" /> -X</Button>
          <Button size="sm" onClick={() => jog('y', 1)} disabled={!active}><ArrowDown className="w-4 h-4 mr-1" /> +Y</Button>
          <Button size="sm" onClick={() => jog('y', -1)} disabled={!active}><ArrowUp className="w-4 h-4 mr-1" /> -Y</Button>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => api('POST', '/api/teach/confirm', {})} disabled={!status.pending}>
            <Check className="w-4 h-4 mr-1" /> Зафиксировать
          </Button>
          <Button variant="secondary" onClick={() => api('POST', '/api/teach/skip', {})} disabled={!status.pending}>
            <SkipForward className="w-4 h-4 mr-1" /> Пропустить
          </Button>
          <Button variant="secondary" onClick={() => api('POST', '/api/teach/undo', {})} disabled={!active}>
            <Undo2 className="w-4 h-4 mr-1" /> Отменить шаг
          </Button>
        </div>
      </Card>

      {/* Saved Sequences */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-bold">Сохранённые последовательности</h3>
          <Button size="sm" variant="outline" onClick={loadSequences}>Обновить</Button>
        </div>
        {Object.keys(sequences).length === 0 ? (
          <p className="text-slate-500 text-sm">Нет сохранённых последовательностей</p>
        ) : (
          <div className="space-y-2">
            {Object.entries(sequences).map(([name, steps]) => (
              <div key={name} className="flex items-center justify-between bg-slate-50 rounded p-3">
                <div>
                  <span className="font-medium">{name}</span>
                  <span className="text-slate-500 text-sm ml-2">({Array.isArray(steps) ? steps.length : 0} шагов)</span>
                </div>
                <Button size="sm" onClick={() => playSequence(name)}>
                  <Play className="w-4 h-4 mr-1" /> Запуск
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
