# BookCabinet API Reference

All endpoints are served by the TypeScript Express server (`server/routes.ts`).
Base URL: `http://<host>:5000`

WebSocket: `ws://<host>:5000/ws`

---

## System

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/status` | - | `SystemStatus` | Current system state, position, sensors |
| POST | `/api/maintenance` | `{ enabled: boolean }` | `{ success, maintenanceMode }` | Toggle maintenance mode |
| POST | `/api/emergency-stop` | - | `{ success, message }` | Emergency stop all motors |
| GET | `/api/diagnostics` | - | `{ sensors, motors, rfid, system }` | Full diagnostics snapshot |

## Authentication

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| POST | `/api/auth/card` | `{ rfid: string }` | `{ success, user, reservedBooks, needsExtraction }` | Authenticate by RFID card |
| POST | `/api/auth/logout` | - | `{ success }` | End current session |
| GET | `/api/auth/session` | - | `{ authenticated, user? }` | Check current session |

## Cells (Cabinet Slots)

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/cells` | - | `Cell[]` | All 126 cells |
| GET | `/api/cells/extraction` | - | `Cell[]` | Cells needing book extraction |
| GET | `/api/cells/available/:row?` | - | `Cell[]` | Available (empty) cells |
| GET | `/api/cells/:id` | - | `Cell` | Single cell by ID |
| PATCH | `/api/cells/:id` | Partial `Cell` | `Cell` | Update cell fields |

## Users

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/users` | - | `User[]` | All users |
| GET | `/api/users/:id` | - | `User` | Single user |
| GET | `/api/users/rfid/:rfid` | - | `User` | Find user by RFID |
| POST | `/api/users` | `InsertUser` | `User` | Create user |

## Books

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/books` | - | `Book[]` | All books |
| GET | `/api/books/:id` | - | `Book` | Single book |
| GET | `/api/books/rfid/:rfid` | - | `Book` | Find book by RFID |
| GET | `/api/books/reserved/:userRfid` | - | `Book[]` | Books reserved for user |
| POST | `/api/books` | `InsertBook` | `Book` | Create book record |
| PATCH | `/api/books/:id` | Partial `Book` | `Book` | Update book |

## Business Operations

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| POST | `/api/issue` | `{ bookRfid, userRfid }` | `{ success, book?, cell? }` | Issue book to user (mechanical + DB) |
| POST | `/api/return` | `{ bookRfid }` | `{ success, book?, cell? }` | Return book to cabinet |
| POST | `/api/reserve` | `{ bookRfid, userRfid }` | `{ success, message }` | Reserve book for user |
| POST | `/api/cancel-reservation` | `{ bookRfid, userRfid }` | `{ success, message }` | Cancel reservation |
| POST | `/api/load-book` | `{ bookRfid, title, author? }` | `{ success, message }` | Load new book into cabinet |
| POST | `/api/extract` | `{ cellId }` | `{ success, book? }` | Extract single book from cell |
| POST | `/api/extract-all` | - | `{ success, extracted }` | Extract all returned books |
| POST | `/api/run-inventory` | - | `{ success, found, missing }` | Run full inventory scan |

## Cabinet State

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/cabinet/state` | - | Cabinet state object | Current cabinet service state |
| POST | `/api/cabinet/clear-error` | - | `{ success }` | Clear cabinet error state |

## Operations Log

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/operations` | `?limit=N` | `Operation[]` | All operations (optional limit) |
| GET | `/api/operations/today` | - | `Operation[]` | Today's operations |
| POST | `/api/operations` | `InsertOperation` | `Operation` | Create operation record |

## Statistics

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/statistics` | - | `Statistics` | Aggregated statistics |

## System Logs

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/logs` | `?limit=N` | `SystemLog[]` | System logs |
| DELETE | `/api/logs` | - | `{ success }` | Clear all logs |

## RFID

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/rfid-readers` | - | Reader status array | Status of all 3 RFID readers |
| GET | `/api/rfid-test/:readerId` | - | SSE stream | Live RFID reader test (30s SSE) |
| GET | `/api/ports` | - | `{ ports }` | Available serial ports |
| GET | `/api/reader-configs` | - | `{ configs }` | Reader configurations |
| POST | `/api/connect` | `{ port, readerType, baudRate? }` | `{ success }` | Connect to RFID reader |
| POST | `/api/disconnect` | - | `{ success }` | Disconnect RFID reader |
| POST | `/api/inventory` | - | `{ success }` | Start RFID inventory scan |

## Tags

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/tags` | - | `RfidTag[]` | All seen RFID tags |
| DELETE | `/api/tags` | - | `{ success }` | Clear all tags |

## Simulation (Development)

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| POST | `/api/simulate-tag-read` | `{ epc, rssi?, timestamp? }` | `{ success, tag }` | Simulate UHF tag read |
| POST | `/api/simulate-card-read` | `{ rfid }` | `{ success }` | Simulate NFC card tap |

## Motor Testing

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| POST | `/api/test/motor` | `{ command, axis?, steps?, speed? }` | `{ success, position }` | Test XY motors (move/home) |
| POST | `/api/test/tray` | `{ command }` | `{ success, position }` | Test tray (extend/retract) |
| POST | `/api/test/servo` | `{ servo, command }` | `{ success, locks }` | Test servo locks (open/close) |
| POST | `/api/test/shutter` | `{ shutter, command }` | `{ success, shutters }` | Test shutters (open/close) |
| POST | `/api/test/sensors` | - | `{ success, sensors }` | Read all sensor states |

## Shutters (Direct GPIO)

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| POST | `/api/shutter/:action` | - | `{ success, action }` | Direct shutter control (open-outer, close-outer, open-inner, close-inner, open-all, close-all) |

## Calibration

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/calibration` | - | `CalibrationData` | Current calibration data |
| POST | `/api/calibration` | Partial `CalibrationData` | `{ success, calibration }` | Update calibration (merge) |
| GET | `/api/calibration/export` | - | `{ success, data, exportedAt }` | Export calibration JSON |
| POST | `/api/calibration/import` | `CalibrationData` | `{ success, calibration }` | Import calibration JSON |
| POST | `/api/calibration/reset` | - | `{ success, calibration }` | Reset to factory defaults |
| POST | `/api/calibration/test-suite` | - | `{ success, results, summary }` | Run all calibration tests |
| POST | `/api/calibration/test/:testName` | `{ x?, y? }` | `{ success, result }` | Run single test (home/tray/servos/shutters/sensors/move-cell) |

## Calibration Wizard

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| POST | `/api/calibration/wizard/kinematics/start` | - | Wizard state | Start kinematics calibration |
| POST | `/api/calibration/wizard/kinematics/step` | `{ action, response? }` | Step result | Kinematics wizard step |
| POST | `/api/calibration/wizard/points10/start` | - | Wizard state | Start 10-point calibration |
| POST | `/api/calibration/wizard/points10/save` | - | Step result | Save current calibration point |
| POST | `/api/calibration/wizard/move` | `{ direction, stepIndex? }` | `{ success, position }` | WASD movement during wizard |
| POST | `/api/calibration/wizard/grab/start` | `{ side }` | Wizard state | Start grab calibration |
| POST | `/api/calibration/wizard/grab/adjust` | `{ side, param, delta }` | `{ success, currentValues }` | Adjust grab parameter |
| POST | `/api/calibration/wizard/grab/test` | `{ side, param }` | `{ success, message }` | Test grab movement |
| GET | `/api/calibration/wizard/state` | - | Wizard state | Current wizard state |
| POST | `/api/calibration/wizard/exit` | - | `{ success }` | Exit wizard mode |

## Blocked Cells

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/calibration/blocked-cells` | - | `{ success, blocked_cells }` | Get blocked cell map |
| POST | `/api/calibration/blocked-cells` | `{ side, column, rows, action }` | `{ success, blocked_cells }` | Block/unblock cells |
| POST | `/api/calibration/blocked-cells/reset` | - | `{ success, blocked_cells }` | Reset blocked cells to defaults |

## Quick Test

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| POST | `/api/calibration/quick-test` | `{ side, col, row }` | `{ success, steps, targetPosition }` | Quick test single cell |

## Settings

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| GET | `/api/settings` | - | Settings object | All system settings |
| POST | `/api/settings` | Settings object | `{ success }` | Save settings |

## Teach Mode

| Method | Endpoint | Request Body | Response | Description |
|--------|----------|-------------|----------|-------------|
| POST | `/api/teach/start` | `{ name }` | `{ success }` | Start recording sequence |
| POST | `/api/teach/execute` | `{ action, params }` | `{ success, stepIndex }` | Execute and record action |
| POST | `/api/teach/jog` | `{ axis, steps }` | `{ success, position }` | Jog movement during teach |
| POST | `/api/teach/confirm` | - | `{ success }` | Confirm last step |
| POST | `/api/teach/skip` | - | `{ success }` | Skip last step |
| POST | `/api/teach/undo` | - | `{ success, stepsCount }` | Undo last step |
| POST | `/api/teach/save` | - | `{ success }` | Save recorded sequence |
| POST | `/api/teach/discard` | - | `{ success }` | Discard recording |
| GET | `/api/teach/status` | - | `{ active, name, stepsCount, pending }` | Current teach status |
| GET | `/api/teach/sequences` | - | `Record<string, Step[]>` | All saved sequences |
| POST | `/api/teach/play` | `{ name }` | `{ success, steps }` | Play saved sequence |

---

## WebSocket Messages

Connect to `ws://<host>:5000/ws`. Messages are JSON with `{ type, data }` structure.

### Server -> Client

| Type | Data | Description |
|------|------|-------------|
| `status` | `SystemStatus` | System state update |
| `tag_read` | `TagReadEvent` | UHF tag detected |
| `card_read` | `{ uid, cardType, timestamp }` | NFC card tapped |
| `reader_status` | `RfidReaderStatus` | Reader connection status |
| `cabinet_state` | Cabinet state | Cabinet service state change |
| `operation_started` | Operation data | Operation began |
| `operation_completed` | Operation data | Operation finished |
| `operation_failed` | Operation data | Operation failed |
| `cell_opened` | Position | Cell physically opened |
| `book_detected` | `{ rfid }` | Book detected in window |
| `position` | `{ x, y, tray, timestamp }` | Motor position update |
| `progress` | Progress data | Operation progress update |
| `statistics` | `Statistics` | Periodic stats broadcast |

### Client -> Server

| Action | Fields | Description |
|--------|--------|-------------|
| `authenticate` | `{ card_rfid }` | Trigger card authentication |
| `get_status` | - | Request current status |
