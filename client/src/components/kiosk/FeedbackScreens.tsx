import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, XCircle, AlertTriangle, Loader2 } from "lucide-react";

interface ProgressScreenProps {
  message: string;
  value: number;
}

export function ProgressScreen({ message, value }: ProgressScreenProps) {
  return (
    <div className="min-h-screen bg-slate-100 flex flex-col items-center justify-center p-8" data-testid="screen-progress">
      <Loader2 className="w-16 h-16 text-blue-500 animate-spin mb-6" />
      <h2 className="text-2xl font-bold text-slate-800 mb-4">{message || 'Выполняется операция...'}</h2>
      <div className="w-80">
        <Progress value={value} className="h-3" />
      </div>
    </div>
  );
}

interface SuccessScreenProps {
  message: string;
  onContinue: () => void;
}

export function SuccessScreen({ message, onContinue }: SuccessScreenProps) {
  return (
    <div className="min-h-screen bg-slate-100 flex flex-col items-center justify-center p-8" data-testid="screen-success">
      <CheckCircle2 className="w-24 h-24 text-green-500 mb-6" />
      <h2 className="text-3xl font-bold text-slate-800 mb-4">Успешно!</h2>
      <p className="text-xl text-slate-600 mb-8 text-center max-w-lg">{message}</p>
      <Button size="lg" className="h-16 px-10 text-xl" onClick={onContinue} data-testid="button-continue">
        Продолжить
      </Button>
    </div>
  );
}

interface ErrorScreenProps {
  message: string;
  onBack: () => void;
}

export function ErrorScreen({ message, onBack }: ErrorScreenProps) {
  return (
    <div className="min-h-screen bg-slate-100 flex flex-col items-center justify-center p-8" data-testid="screen-error">
      <XCircle className="w-24 h-24 text-red-500 mb-6" />
      <h2 className="text-3xl font-bold text-slate-800 mb-4">Ошибка</h2>
      <p className="text-xl text-slate-600 mb-8 text-center max-w-lg">{message}</p>
      <Button size="lg" variant="destructive" className="h-16 px-10 text-xl" onClick={onBack}>
        Назад
      </Button>
    </div>
  );
}

export function MaintenanceScreen() {
  return (
    <div className="min-h-screen bg-slate-100 flex flex-col items-center justify-center p-8" data-testid="screen-maintenance">
      <AlertTriangle className="w-24 h-24 text-amber-500 mb-6" />
      <h2 className="text-3xl font-bold text-slate-800 mb-4">Обслуживание</h2>
      <p className="text-xl text-slate-600">Шкаф временно недоступен. Обратитесь к библиотекарю.</p>
    </div>
  );
}
