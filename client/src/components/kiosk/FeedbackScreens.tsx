import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, XCircle, AlertTriangle, Loader2 } from "lucide-react";

interface ProgressScreenProps {
  message: string;
  value: number;
}

export function ProgressScreen({ message, value }: ProgressScreenProps) {
  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center p-8" data-testid="screen-progress">
      <Loader2 className="w-16 h-16 text-black animate-spin mb-6" />
      <h2 className="text-2xl font-bold text-black mb-4">{message || 'Выполняется операция...'}</h2>
      <div className="w-80">
        <Progress value={value} className="h-3" />
      </div>
    </div>
  );
}

interface SuccessScreenProps {
  message: string;
  onContinue: () => void;
  autoReturnMs?: number;
}

export function SuccessScreen({ message, onContinue, autoReturnMs = 5000 }: SuccessScreenProps) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-return to idle after 5 seconds
  useEffect(() => {
    timerRef.current = setTimeout(() => {
      onContinue();
    }, autoReturnMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [onContinue, autoReturnMs]);

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center p-8" data-testid="screen-success">
      {/* Green checkmark with animation */}
      <div className="relative mb-6">
        <div className="absolute inset-0 rounded-full bg-green-100 animate-ping opacity-30" style={{ width: 96, height: 96 }} />
        <CheckCircle2 className="w-24 h-24 text-green-600 relative z-10 animate-bounce-once" />
      </div>
      <h2 className="text-3xl font-bold text-black mb-4">Успешно!</h2>
      <p className="text-xl text-black mb-8 text-center max-w-lg">{message}</p>
      <Button size="lg" className="h-16 px-10 text-xl" onClick={onContinue} data-testid="button-continue">
        Продолжить
      </Button>
      <p className="text-sm text-black mt-4">Автоматический переход через 5 секунд</p>
    </div>
  );
}

interface ErrorScreenProps {
  message: string;
  onBack: () => void;
  autoReturnMs?: number;
}

export function ErrorScreen({ message, onBack, autoReturnMs = 5000 }: ErrorScreenProps) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-return to idle after 5 seconds
  useEffect(() => {
    timerRef.current = setTimeout(() => {
      onBack();
    }, autoReturnMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [onBack, autoReturnMs]);

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center p-8" data-testid="screen-error">
      <XCircle className="w-24 h-24 text-red-500 mb-6" />
      <h2 className="text-3xl font-bold text-black mb-4">Ошибка</h2>
      <p className="text-xl text-black mb-8 text-center max-w-lg">{message}</p>
      <Button size="lg" variant="destructive" className="h-16 px-10 text-xl" onClick={onBack}>
        Начать заново
      </Button>
      <p className="text-sm text-black mt-4">Автоматический переход через 5 секунд</p>
    </div>
  );
}

export function MaintenanceScreen() {
  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center p-8" data-testid="screen-maintenance">
      <AlertTriangle className="w-24 h-24 text-black mb-6" />
      <h2 className="text-3xl font-bold text-black mb-4">Обслуживание</h2>
      <p className="text-xl text-black">Шкаф временно недоступен. Обратитесь к библиотекарю.</p>
    </div>
  );
}
