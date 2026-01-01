import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { BookOpen, Package, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';

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
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);

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
      case 'empty': return '#e2e8f0';
      case 'occupied': return '#22c55e';
      case 'reserved': return '#3b82f6';
      case 'needs_extraction': return '#f59e0b';
      default: return '#94a3b8';
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

  const handleCellClick = (cell: Cell) => {
    setSelectedCell(cell);
    onCellClick?.(cell);
  };

  const cellWidth = 35;
  const cellHeight = 25;
  const cellGap = 4;
  const rowGap = 60;
  const columnGap = 20;

  const svgWidth = (COLUMNS * (POSITIONS * (cellWidth + cellGap) + columnGap)) + 100;
  const svgHeight = (ROWS.length * (cellHeight + rowGap)) + 100;

  return (
    <div className="flex gap-4 h-full" data-testid="cabinet-viewer">
      <div className="flex-1 bg-slate-900 rounded-xl p-4 overflow-hidden">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-white text-lg font-bold">3D-модель шкафа</h3>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setZoom(z => Math.min(z + 0.2, 2))}
              data-testid="button-zoom-in"
            >
              <ZoomIn className="w-4 h-4" />
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setZoom(z => Math.max(z - 0.2, 0.5))}
              data-testid="button-zoom-out"
            >
              <ZoomOut className="w-4 h-4" />
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setRotation(r => (r + 15) % 360)}
              data-testid="button-rotate"
            >
              <RotateCcw className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div 
          className="overflow-auto"
          style={{ 
            transform: `scale(${zoom}) perspective(1000px) rotateX(${rotation > 180 ? rotation - 360 : rotation}deg)`,
            transformOrigin: 'center center',
            transition: 'transform 0.3s ease'
          }}
        >
          <svg 
            width={svgWidth} 
            height={svgHeight} 
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            className="mx-auto"
          >
            <defs>
              <linearGradient id="cabinetGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#475569" />
                <stop offset="100%" stopColor="#1e293b" />
              </linearGradient>
              <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="2" dy="2" stdDeviation="3" floodOpacity="0.3"/>
              </filter>
            </defs>

            <rect 
              x="20" 
              y="20" 
              width={svgWidth - 40} 
              height={svgHeight - 40} 
              rx="8" 
              fill="url(#cabinetGrad)"
              filter="url(#shadow)"
            />

            {ROWS.map((row, rowIndex) => (
              <g key={row}>
                <text 
                  x="40" 
                  y={60 + rowIndex * (cellHeight + rowGap) + cellHeight / 2}
                  fill="white"
                  fontSize="16"
                  fontWeight="bold"
                  dominantBaseline="middle"
                >
                  Ряд {row}
                </text>

                {Array.from({ length: COLUMNS }).map((_, colIndex) => (
                  <g key={`${row}-${colIndex}`}>
                    <text
                      x={80 + colIndex * (POSITIONS * (cellWidth + cellGap) + columnGap) + (POSITIONS * (cellWidth + cellGap)) / 2}
                      y={45 + rowIndex * (cellHeight + rowGap)}
                      fill="#94a3b8"
                      fontSize="12"
                      textAnchor="middle"
                    >
                      Колонка {colIndex + 1}
                    </text>

                    {Array.from({ length: POSITIONS }).map((_, posIndex) => {
                      const cell = getCell(row, colIndex, posIndex);
                      const x = 80 + colIndex * (POSITIONS * (cellWidth + cellGap) + columnGap) + posIndex * (cellWidth + cellGap);
                      const y = 55 + rowIndex * (cellHeight + rowGap);
                      const isSelected = selectedCell?.id === cell?.id;

                      return (
                        <g 
                          key={`${row}-${colIndex}-${posIndex}`}
                          onClick={() => cell && handleCellClick(cell)}
                          style={{ cursor: 'pointer' }}
                          data-testid={`cell-${row}-${colIndex}-${posIndex}`}
                        >
                          <rect
                            x={x}
                            y={y}
                            width={cellWidth}
                            height={cellHeight}
                            rx="3"
                            fill={cell ? getCellColor(cell.status) : '#64748b'}
                            stroke={isSelected ? '#ffffff' : '#334155'}
                            strokeWidth={isSelected ? 2 : 1}
                            className="transition-all duration-200 hover:opacity-80"
                          />
                          {cell?.status === 'occupied' && (
                            <rect
                              x={x + 8}
                              y={y + 5}
                              width={cellWidth - 16}
                              height={cellHeight - 10}
                              rx="2"
                              fill="#166534"
                            />
                          )}
                          <text
                            x={x + cellWidth / 2}
                            y={y + cellHeight / 2}
                            fill={cell?.status === 'empty' ? '#64748b' : '#ffffff'}
                            fontSize="8"
                            textAnchor="middle"
                            dominantBaseline="middle"
                          >
                            {posIndex + 1}
                          </text>
                        </g>
                      );
                    })}
                  </g>
                ))}
              </g>
            ))}

            <g transform={`translate(${svgWidth - 180}, 50)`}>
              <text x="0" y="0" fill="white" fontSize="12" fontWeight="bold">Легенда:</text>
              {[
                { color: '#e2e8f0', label: 'Пустая' },
                { color: '#22c55e', label: 'Занята' },
                { color: '#3b82f6', label: 'Забронирована' },
                { color: '#f59e0b', label: 'Требует изъятия' }
              ].map((item, i) => (
                <g key={item.label} transform={`translate(0, ${20 + i * 22})`}>
                  <rect x="0" y="0" width="16" height="16" rx="2" fill={item.color} />
                  <text x="22" y="12" fill="#94a3b8" fontSize="10">{item.label}</text>
                </g>
              ))}
            </g>
          </svg>
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
                  <Badge variant="outline">
                    {selectedCell.row}-{selectedCell.x + 1}-{selectedCell.y + 1}
                  </Badge>
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

export function CabinetViewerDemo() {
  const demoCells: Cell[] = [];
  let id = 0;
  
  for (const row of ROWS) {
    for (let x = 0; x < COLUMNS; x++) {
      for (let y = 0; y < POSITIONS; y++) {
        const random = Math.random();
        let status: Cell['status'] = 'empty';
        let bookRfid: string | undefined;
        let bookTitle: string | undefined;
        let bookAuthor: string | undefined;

        if (random > 0.6) {
          status = 'occupied';
          bookRfid = `RFID${String(id).padStart(6, '0')}`;
          bookTitle = `Книга №${id}`;
          bookAuthor = `Автор ${id}`;
        } else if (random > 0.5) {
          status = 'reserved';
          bookRfid = `RFID${String(id).padStart(6, '0')}`;
          bookTitle = `Забронированная книга №${id}`;
          bookAuthor = `Автор ${id}`;
        } else if (random > 0.45) {
          status = 'needs_extraction';
          bookRfid = `RFID${String(id).padStart(6, '0')}`;
          bookTitle = `Возвращённая книга №${id}`;
          bookAuthor = `Автор ${id}`;
        }

        demoCells.push({ id: id++, row, x, y, status, bookRfid, bookTitle, bookAuthor });
      }
    }
  }

  return <CabinetViewer cells={demoCells} />;
}
