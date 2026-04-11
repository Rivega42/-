import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { Save, RefreshCw, Send, Database, Bell, Clock, Globe } from "lucide-react";

interface SettingsData {
  timeouts: { move: number; tray_extend: number; user_wait: number };
  telegram: { enabled: boolean; bot_token: string; chat_id: string };
  backup: { enabled: boolean; interval: number };
  irbis: { host: string; port: number; mock: boolean };
}

const DEFAULT_SETTINGS: SettingsData = {
  timeouts: { move: 1500, tray_extend: 800, user_wait: 30000 },
  telegram: { enabled: false, bot_token: '', chat_id: '' },
  backup: { enabled: true, interval: 24 },
  irbis: { host: '172.29.67.70', port: 6666, mock: true },
};

export default function SettingsPanel() {
  const [settings, setSettings] = useState<SettingsData>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    try {
      const res = await apiRequest('GET', '/api/settings');
      const data = await res.json();
      setSettings({ ...DEFAULT_SETTINGS, ...data });
    } catch {}
    setLoading(false);
  }

  async function saveSettings() {
    setSaving(true);
    try {
      await apiRequest('POST', '/api/settings', settings);
      toast({ title: 'Сохранено', description: 'Настройки обновлены' });
    } catch (e: any) {
      toast({ title: 'Ошибка', description: e.message, variant: 'destructive' });
    }
    setSaving(false);
  }

  const update = (section: keyof SettingsData, field: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [section]: { ...prev[section], [field]: value },
    }));
  };

  if (loading) return <div className="text-center py-8 text-slate-500">Загрузка...</div>;

  return (
    <div className="space-y-5">
      <Card className="p-5">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5" /> Таймауты (мс)
        </h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label>Перемещение XY (мс)</Label>
            <Input type="number" value={settings.timeouts.move}
              onChange={e => update('timeouts', 'move', parseInt(e.target.value) || 0)} />
          </div>
          <div>
            <Label>Выдвижение лотка (мс)</Label>
            <Input type="number" value={settings.timeouts.tray_extend}
              onChange={e => update('timeouts', 'tray_extend', parseInt(e.target.value) || 0)} />
          </div>
          <div>
            <Label>Ожидание пользователя (мс)</Label>
            <Input type="number" value={settings.timeouts.user_wait}
              onChange={e => update('timeouts', 'user_wait', parseInt(e.target.value) || 0)} />
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Bell className="w-5 h-5" /> Telegram уведомления
        </h3>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <Switch checked={settings.telegram.enabled}
              onCheckedChange={v => update('telegram', 'enabled', v)} />
            <Label>Включено</Label>
          </div>
          <div>
            <Label>Bot Token</Label>
            <Input type="password" placeholder="Вставьте токен из @BotFather"
              value={settings.telegram.bot_token}
              onChange={e => update('telegram', 'bot_token', e.target.value)} />
          </div>
          <div>
            <Label>Chat ID</Label>
            <Input placeholder="-100123456789"
              value={settings.telegram.chat_id}
              onChange={e => update('telegram', 'chat_id', e.target.value)} />
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Database className="w-5 h-5" /> Резервное копирование
        </h3>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <Switch checked={settings.backup.enabled}
              onCheckedChange={v => update('backup', 'enabled', v)} />
            <Label>Автобэкап</Label>
          </div>
          <div className="flex items-center gap-2">
            <Label>Интервал (ч):</Label>
            <Input type="number" className="w-24"
              value={settings.backup.interval}
              onChange={e => update('backup', 'interval', parseInt(e.target.value) || 1)} />
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Globe className="w-5 h-5" /> ИРБИС
        </h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label>Хост</Label>
            <Input value={settings.irbis.host}
              onChange={e => update('irbis', 'host', e.target.value)} />
          </div>
          <div>
            <Label>Порт</Label>
            <Input type="number" value={settings.irbis.port}
              onChange={e => update('irbis', 'port', parseInt(e.target.value) || 6666)} />
          </div>
          <div className="flex items-center gap-3 pt-6">
            <Switch checked={settings.irbis.mock}
              onCheckedChange={v => update('irbis', 'mock', v)} />
            <Label>Mock режим</Label>
          </div>
        </div>
      </Card>

      <Button size="lg" className="w-full h-14 text-lg" onClick={saveSettings} disabled={saving}>
        <Save className="w-5 h-5 mr-2" />
        {saving ? 'Сохранение...' : 'Сохранить настройки'}
      </Button>
    </div>
  );
}
