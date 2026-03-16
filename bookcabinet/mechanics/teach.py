"""
Teach mode — режим обучения последовательностям движений.
Позволяет записывать последовательности с джог-коррекцией.
"""
import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


class TeachSession:
    """Активная сессия записи последовательности"""

    def __init__(self, name: str):
        self.name = name
        self.steps: List[Dict[str, Any]] = []
        self.current_position = {"x": 0, "y": 0, "tray": 0}
        self.pending_action: Optional[Dict] = None  # последнее действие, ожидающее /confirm
        self.started_at = datetime.now().isoformat()

    def add_step(self, action: str, params: dict, taught: bool = False):
        """Записать шаг как финальный"""
        self.steps.append({
            "action": action,
            "params": params,
            "taught": taught,
            "timestamp": datetime.now().isoformat()
        })

    def to_sequence(self) -> dict:
        return {
            "name": self.name,
            "created": self.started_at,
            "steps": [{"action": s["action"], "params": s["params"], "taught": s.get("taught", False)}
                      for s in self.steps]
        }


class TeachMode:
    """
    Режим обучения: выполняет команды И записывает их.

    Флоу:
    - execute_action(action, params) → выполнить + запомнить как pending
    - jog(axis, steps) → подвинуть + обновить pending params
    - confirm() → зафиксировать pending как финальный шаг
    - skip() → зафиксировать без изменений
    - undo() → отменить последний шаг
    - save(path) → сохранить последовательность в JSON
    """

    SEQUENCES_DIR = "bookcabinet/sequences"

    def __init__(self):
        self.session: Optional[TeachSession] = None
        self.motors = None
        self.sensors = None

    def set_hardware(self, motors, sensors):
        self.motors = motors
        self.sensors = sensors

    def start(self, name: str) -> str:
        if self.session:
            return f"❌ Уже активна сессия '{self.session.name}'. Сначала /save или /discard"
        self.session = TeachSession(name)
        return f"🔴 Запись начата: '{name}'\nПиши команды. /confirm — зафиксировать позицию, /save — сохранить"

    def is_active(self) -> bool:
        return self.session is not None

    async def execute(self, action: str, params: dict) -> str:
        """Выполнить действие и запомнить как pending"""
        if not self.session:
            return "❌ Сессия не активна. Начни с /record <имя>"

        # Выполнить действие
        result = await self._run_action(action, params)
        if not result["ok"]:
            return f"❌ Ошибка: {result['error']}"

        # Сохранить как pending (требует /confirm или /skip)
        self.session.pending_action = {
            "action": action,
            "params": dict(params),
            "original_params": dict(params)
        }

        pos = self.motors.get_position() if self.motors else {}
        return f"✓ {action} выполнено\n📍 X:{pos.get('x',0)} Y:{pos.get('y',0)} Tray:{pos.get('tray',0)}\nПодстрой джогом или /confirm"

    async def jog(self, axis: str, steps: int) -> str:
        """Джог для уточнения позиции"""
        if not self.session:
            return "❌ Сессия не активна"

        if not self.motors:
            return "❌ Моторы не подключены"

        axis = axis.lower()

        if axis == "x":
            new_x = self.motors.position["x"] + steps
            await self.motors.move_xy(new_x, self.motors.position["y"])
        elif axis == "y":
            new_y = self.motors.position["y"] + steps
            await self.motors.move_xy(self.motors.position["x"], new_y)
        elif axis == "tray":
            if steps > 0:
                await self.motors.extend_tray(abs(steps))
            else:
                await self.motors.retract_tray(abs(steps))
        else:
            return f"❌ Неизвестная ось: {axis}. Используй x, y, tray"

        # Обновить params в pending action если он связан с позицией
        if self.session.pending_action:
            action = self.session.pending_action["action"]
            if action == "move_xy":
                self.session.pending_action["params"]["x"] = self.motors.position["x"]
                self.session.pending_action["params"]["y"] = self.motors.position["y"]
            elif action in ("extend_tray", "retract_tray"):
                self.session.pending_action["params"]["steps"] = (
                    self.session.pending_action["params"].get("steps", 0) + abs(steps)
                )

        pos = self.motors.get_position()
        delta = f"+{steps}" if steps > 0 else str(steps)
        return f"→ джог {axis} {delta}\n📍 X:{pos['x']} Y:{pos['y']} Tray:{pos['tray']}"

    def confirm(self) -> str:
        """Зафиксировать текущее положение как точное"""
        if not self.session:
            return "❌ Сессия не активна"
        if not self.session.pending_action:
            return "❌ Нет незафиксированного действия"

        pa = self.session.pending_action
        self.session.add_step(pa["action"], pa["params"], taught=True)
        self.session.pending_action = None

        return f"✅ Зафиксировано: {pa['action']} {pa['params']}\n({len(self.session.steps)} шагов в последовательности)"

    def skip(self) -> str:
        """Принять исходные параметры без коррекции"""
        if not self.session or not self.session.pending_action:
            return "❌ Нет незафиксированного действия"

        pa = self.session.pending_action
        self.session.add_step(pa["action"], pa["original_params"], taught=False)
        self.session.pending_action = None
        return f"⏭ Принято без коррекции: {pa['action']}"

    def undo(self) -> str:
        """Отменить последний зафиксированный шаг"""
        if not self.session:
            return "❌ Сессия не активна"
        if self.session.pending_action:
            self.session.pending_action = None
            return "↩ Текущее действие отменено"
        if not self.session.steps:
            return "❌ Нет шагов для отмены"

        removed = self.session.steps.pop()
        return f"↩ Отменено: {removed['action']} ({len(self.session.steps)} шагов осталось)"

    def save(self) -> str:
        """Сохранить последовательность в JSON файл"""
        if not self.session:
            return "❌ Нет активной сессии"

        # Зафиксировать pending если есть
        if self.session.pending_action:
            self.skip()

        if not self.session.steps:
            return "❌ Последовательность пуста"

        os.makedirs(self.SEQUENCES_DIR, exist_ok=True)
        filename = f"{self.session.name.replace(' ', '_')}.json"
        filepath = os.path.join(self.SEQUENCES_DIR, filename)

        sequence = self.session.to_sequence()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(sequence, f, ensure_ascii=False, indent=2)

        steps_count = len(self.session.steps)
        name = self.session.name
        self.session = None

        return f"💾 Сохранено: '{name}' ({steps_count} шагов) → {filepath}"

    def discard(self) -> str:
        """Отменить сессию без сохранения"""
        if not self.session:
            return "❌ Нет активной сессии"
        name = self.session.name
        self.session = None
        return f"🗑 Сессия '{name}' отменена"

    def status(self) -> str:
        """Текущий статус"""
        if not self.session:
            return "⏹ Не активна"

        pending = f"⏳ Ожидает /confirm: {self.session.pending_action['action']}" if self.session.pending_action else ""
        return (
            f"🔴 Запись: '{self.session.name}'\n"
            f"📝 Шагов: {len(self.session.steps)}\n"
            f"{pending}"
        ).strip()

    def list_sequences(self) -> str:
        """Список сохранённых последовательностей"""
        if not os.path.exists(self.SEQUENCES_DIR):
            return "📂 Нет сохранённых последовательностей"

        files = [f for f in os.listdir(self.SEQUENCES_DIR) if f.endswith(".json")]
        if not files:
            return "📂 Нет сохранённых последовательностей"

        lines = ["📋 Последовательности:"]
        for f in sorted(files):
            try:
                with open(os.path.join(self.SEQUENCES_DIR, f)) as fh:
                    seq = json.load(fh)
                lines.append(f"• {seq['name']} ({len(seq['steps'])} шагов)")
            except:
                lines.append(f"• {f} (ошибка чтения)")
        return "\n".join(lines)

    async def play(self, name: str, progress_callback=None) -> str:
        """Воспроизвести сохранённую последовательность"""
        filename = f"{name.replace(' ', '_')}.json"
        filepath = os.path.join(self.SEQUENCES_DIR, filename)

        if not os.path.exists(filepath):
            return f"❌ Последовательность '{name}' не найдена"

        with open(filepath) as f:
            sequence = json.load(f)

        steps = sequence.get("steps", [])
        for i, step in enumerate(steps):
            action = step["action"]
            params = step["params"]

            if progress_callback:
                progress_callback(f"Шаг {i+1}/{len(steps)}: {action}")

            result = await self._run_action(action, params)
            if not result["ok"]:
                return f"❌ Ошибка на шаге {i+1} ({action}): {result['error']}"

        return f"✅ '{name}' выполнена ({len(steps)} шагов)"

    async def _run_action(self, action: str, params: dict) -> dict:
        """Выполнить одно действие"""
        if not self.motors:
            return {"ok": False, "error": "моторы не подключены"}

        try:
            if action == "move_xy":
                ok = await self.motors.move_xy(params["x"], params["y"])
            elif action == "extend_tray":
                ok = await self.motors.extend_tray(params.get("steps", 3000))
            elif action == "retract_tray":
                ok = await self.motors.retract_tray(params.get("steps", 3000))
            elif action == "wait":
                await asyncio.sleep(params.get("ms", 1000) / 1000)
                ok = True
            elif action == "home":
                ok = await self.motors.home()
            else:
                return {"ok": False, "error": f"неизвестное действие: {action}"}

            return {"ok": ok}
        except Exception as e:
            return {"ok": False, "error": str(e)}


teach_mode = TeachMode()
