import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BookOpen, Package } from 'lucide-react';

interface Cell {
  id: number;
  row: string;
  x: number;
  y: number;
  status: 'empty' | 'occupied' | 'reserved' | 'needs_extraction';
  bookRfid?: string;
  bookTitle?: string;
  bookAuthor?: string;
}

interface CabinetViewerProps {
  cells: Cell[];
  onCellClick?: (cell: Cell) => void;
}

const ROWS = ['A', 'B'];
const COLUMNS = 3;
const POSITIONS = 21;

export function CabinetViewer({ cells, onCellClick }: CabinetViewerProps) {
  const [selectedCell, setSelectedCell] = useState<Cell | null>(null);

  const cellMap = useMemo(() => {
    const map = new Map<string, Cell>();
    cells.forEach(cell => {
      const key = `${cell.row}-${cell.x}-${cell.y}`;
      map.set(key, cell);
    });
    return map;
  }, [cells]);

  const getCell = (row: string, x: number, y: number): Cell | undefined => {
    return cellMap.get(`${row}-${x}-${y}`);
  };

  const getCellColor = (status: string) => {
    switch (status) {
      case 'empty': return 'bg-slate-200 dark:bg-slate-700';
      case 'occupied': return 'bg-green-500';
      case 'reserved': return 'bg-blue-500';
      case 'needs_extraction': return 'bg-amber-500';
      default: return 'bg-slate-400';
    }
  };

  const getCellStatusText = (status: string) => {
    switch (status) {
      case 'empty': return 'Пустая';
      case 'occupied': return 'Занята';
      case 'reserved': return 'Забронирована';
      case 'needs_extraction': return 'Требуется изъятие';
      default: return 'Неизвестно';
    }
  };

  const handleCellClick = (cell: Cell | undefined, row: string, col: number, pos: number) => {
    const cellData = cell || {
      id: row === 'A' ? col * POSITIONS + pos : COLUMNS * POSITIONS + col * POSITIONS + pos,
      row,
      x: col,
      y: pos,
      status: 'empty' as const
    };
    setSelectedCell(cellData);
    onCellClick?.(cellData);
  };

  const stats = useMemo(() => {
    let empty = 0, occupied = 0, reserved = 0, needsExtraction = 0;
    cells.forEach(cell => {
      switch (cell.status) {
        case 'empty': empty++; break;
        case 'occupied': occupied++; break;
        case 'reserved': reserved++; break;
        case 'needs_extraction': needsExtraction++; break;
      }
    });
    const total = ROWS.length * COLUMNS * POSITIONS;
    return { empty: total - occupied - reserved - needsExtraction, occupied, reserved, needsExtraction, total };
  }, [cells]);

  return (
    <div className="flex gap-4 h-full" data-testid="cabinet-viewer">
      <div className="flex-1 bg-slate-900 rounded-xl p-4 overflow-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-white text-lg font-bold">Схема шкафа (126 ячеек)</h3>
          <div className="flex gap-3 text-xs">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-slate-400"></div>
              <span className="text-slate-400">Пусто ({stats.empty})</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-green-500"></div>
              <span className="text-slate-400">Занято ({stats.occupied})</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-blue-500"></div>
              <span className="text-slate-400">Забронировано ({stats.reserved})</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-amber-500"></div>
              <span className="text-slate-400">Изъятие ({stats.needsExtraction})</span>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {Array.from({ length: COLUMNS }).map((_, colIndex) => (
            <div key={colIndex} className="bg-slate-800 rounded-lg p-4">
              <h4 className="text-slate-300 text-sm font-medium mb-3">Колонка {colIndex + 1}</h4>
              
              <div className="space-y-3">
                {ROWS.map(row => (
                  <div key={`${colIndex}-${row}`} className="flex items-center gap-2">
                    <span className="text-slate-400 text-xs w-8 shrink-0">Ряд {row}</span>
                    <div className="flex flex-wrap gap-1">
                      {Array.from({ length: POSITIONS }).map((_, posIndex) => {
                        const cell = getCell(row, colIndex, posIndex);
                        const isSelected = selectedCell && 
                          selectedCell.row === row && 
                          selectedCell.x === colIndex && 
                          selectedCell.y === posIndex;

                        return (
                          <button
                            key={`${row}-${colIndex}-${posIndex}`}
                            onClick={() => handleCellClick(cell, row, colIndex, posIndex)}
                            className={`
                              w-7 h-7 rounded text-xs font-medium transition-all
                              ${cell ? getCellColor(cell.status) : 'bg-slate-600'}
                              ${isSelected ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800' : ''}
                              ${cell?.status === 'occupied' || cell?.status === 'reserved' || cell?.status === 'needs_extraction' 
                                ? 'text-white' 
                                : 'text-slate-500'}
                              hover:opacity-80 active:scale-95
                            `}
                            data-testid={`cell-${row}-${colIndex}-${posIndex}`}
                          >
                            {posIndex + 1}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <Card className="w-80 flex-shrink-0">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Package className="w-5 h-5" />
            Информация о ячейке
          </CardTitle>
        </CardHeader>
        <CardContent>
          {selectedCell ? (
            <div className="space-y-4" data-testid="cell-info">
              <div className="bg-slate-100 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-slate-500">Позиция</span>
                  <Badge variant="outline" className="font-mono">
                    {selectedCell.row}{selectedCell.x + 1}-{String(selectedCell.y + 1).padStart(2, '0')}
                  </Badge>
                </div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-slate-500">Колонка</span>
                  <span className="font-medium">{selectedCell.x + 1}</span>
                </div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-slate-500">Ряд</span>
                  <span className="font-medium">{selectedCell.row}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">Статус</span>
                  <Badge 
                    variant={selectedCell.status === 'empty' ? 'secondary' : 'default'}
                    className={
                      selectedCell.status === 'occupied' ? 'bg-green-500' :
                      selectedCell.status === 'reserved' ? 'bg-blue-500' :
                      selectedCell.status === 'needs_extraction' ? 'bg-amber-500' : ''
                    }
                  >
                    {getCellStatusText(selectedCell.status)}
                  </Badge>
                </div>
              </div>

              {selectedCell.bookRfid && (
                <div className="border rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <BookOpen className="w-4 h-4 text-blue-500" />
                    <span className="font-medium">Книга</span>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-slate-500">RFID:</span>
                      <span className="ml-2 font-mono text-xs bg-slate-100 px-2 py-1 rounded">
                        {selectedCell.bookRfid}
                      </span>
                    </div>
                    {selectedCell.bookTitle && (
                      <div>
                        <span className="text-slate-500">Название:</span>
                        <p className="font-medium">{selectedCell.bookTitle}</p>
                      </div>
                    )}
                    {selectedCell.bookAuthor && (
                      <div>
                        <span className="text-slate-500">Автор:</span>
                        <p>{selectedCell.bookAuthor}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {!selectedCell.bookRfid && selectedCell.status === 'empty' && (
                <div className="text-center py-4 text-slate-400 border rounded-lg">
                  <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Ячейка пуста</p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-400">
              <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Выберите ячейку для просмотра информации</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
