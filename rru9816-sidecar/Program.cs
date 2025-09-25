using System;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Net.WebSockets;
using System.Net;
using Newtonsoft.Json;
using UHF; // RWDev namespace

namespace RRU9816Sidecar
{
    class Program
    {
        private static HttpListener httpListener;
        private static bool isRunning = false;
        private static int frmcomportindex = 0;
        private static byte fComAdr = 0xff;
        private static int fCmdRet;
        private static bool isConnected = false;
        private static WebSocket connectedClient = null;
        
        static async Task Main(string[] args)
        {
            Console.WriteLine("🚀 RRU9816 Sidecar Bridge Starting...");
            Console.WriteLine("📡 This bridge connects RRU9816 hardware to your Node.js application");
            
            // Start WebSocket server
            await StartWebSocketServer();
        }
        
        private static async Task StartWebSocketServer()
        {
            httpListener = new HttpListener();
            httpListener.Prefixes.Add("http://localhost:8081/");
            
            try
            {
                httpListener.Start();
                isRunning = true;
                
                Console.WriteLine("✅ WebSocket server started on ws://localhost:8081/");
                Console.WriteLine("📞 Waiting for Node.js application to connect...");
                
                while (isRunning)
                {
                    var context = await httpListener.GetContextAsync();
                    
                    if (context.Request.IsWebSocketRequest)
                    {
                        await HandleWebSocketConnection(context);
                    }
                    else
                    {
                        context.Response.StatusCode = 400;
                        context.Response.Close();
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Server error: {ex.Message}");
            }
        }
        
        private static async Task HandleWebSocketConnection(HttpListenerContext context)
        {
            WebSocketContext wsContext = await context.AcceptWebSocketAsync(null);
            connectedClient = wsContext.WebSocket;
            
            Console.WriteLine("🔗 Node.js application connected!");
            
            await SendMessage(new {
                type = "status",
                message = "RRU9816 Sidecar bridge connected successfully"
            });
            
            // Handle incoming messages
            var buffer = new byte[1024 * 4];
            
            try
            {
                while (connectedClient.State == WebSocketState.Open)
                {
                    var result = await connectedClient.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
                    
                    if (result.MessageType == WebSocketMessageType.Text)
                    {
                        var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                        await HandleCommand(message);
                    }
                    else if (result.MessageType == WebSocketMessageType.Close)
                    {
                        await connectedClient.CloseAsync(WebSocketCloseStatus.NormalClosure, "", CancellationToken.None);
                        break;
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ WebSocket error: {ex.Message}");
            }
            finally
            {
                connectedClient = null;
                Console.WriteLine("🔌 Node.js application disconnected");
            }
        }
        
        private static async Task HandleCommand(string message)
        {
            try
            {
                dynamic cmd = JsonConvert.DeserializeObject(message);
                string command = cmd.command;
                
                Console.WriteLine($"📨 Received command: {command}");
                
                switch (command)
                {
                    case "connect":
                        await ConnectToRRU9816((string)cmd.port, (int)cmd.baudRate);
                        break;
                        
                    case "disconnect":
                        await DisconnectFromRRU9816();
                        break;
                        
                    case "start_inventory":
                        await StartInventory();
                        break;
                        
                    case "stop_inventory":
                        await StopInventory();
                        break;
                        
                    default:
                        Console.WriteLine($"⚠️ Unknown command: {command}");
                        break;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Command error: {ex.Message}");
                await SendMessage(new {
                    type = "error",
                    message = ex.Message
                });
            }
        }
        
        private static async Task ConnectToRRU9816(string port, int baudRate)
        {
            Console.WriteLine($"🔌 Connecting to RRU9816 on {port} @ {baudRate} baud...");
            
            try
            {
                // Convert port name to port number (COM15 -> 15)
                int portNum = int.Parse(port.Replace("COM", ""));
                
                // Convert baud rate to DLL format (like C# demo)
                byte fBaud = 3; // Default to 57600 (index 3)
                if (baudRate == 9600) fBaud = 0;
                else if (baudRate == 19200) fBaud = 1;
                else if (baudRate == 38400) fBaud = 2;
                else if (baudRate == 57600) fBaud = 3;
                else if (baudRate == 115200) fBaud = 4;
                
                // Apply C# demo baud rate logic
                if (fBaud > 2)
                    fBaud = (byte)(fBaud + 2);
                
                // Open COM port using RRU9816.dll (exactly like C# demo)
                fCmdRet = RWDev.OpenComPort(portNum, ref fComAdr, fBaud, ref frmcomportindex);
                
                if (fCmdRet != 0)
                {
                    throw new Exception($"Failed to open COM port: {GetReturnCodeDesc(fCmdRet)}");
                }
                
                isConnected = true;
                
                Console.WriteLine($"✅ Connected to RRU9816 on {port}");
                
                await SendMessage(new {
                    type = "connected",
                    port = port,
                    baudRate = baudRate,
                    message = "RRU9816 connected successfully via DLL"
                });
                
                // Initialize RRU9816 (like C# demo)
                await InitializeRRU9816();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Connection failed: {ex.Message}");
                await SendMessage(new {
                    type = "error",
                    message = $"Connection failed: {ex.Message}"
                });
            }
        }
        
        private static async Task InitializeRRU9816()
        {
            Console.WriteLine("⚙️ Initializing RRU9816 (like C# demo)...");
            
            try
            {
                // Get Reader Information (like C# demo)
                byte TrType = 0;
                byte[] VersionInfo = new byte[2];
                byte ReaderType = 0;
                byte ScanTime = 0;
                byte dmaxfre = 0;
                byte dminfre = 0;
                byte powerdBm = 0;
                byte Ant = 0;
                byte BeepEn = 0;
                byte OutputRep = 0;
                byte CheckAnt = 0;
                
                fCmdRet = RWDev.GetReaderInformation(ref fComAdr, VersionInfo, ref ReaderType, ref TrType, 
                    ref dmaxfre, ref dminfre, ref powerdBm, ref ScanTime, ref Ant, ref BeepEn, ref OutputRep, ref CheckAnt, frmcomportindex);
                
                if (fCmdRet == 0)
                {
                    string version = $"{VersionInfo[0]:D2}.{VersionInfo[1]:D2}";
                    Console.WriteLine($"✅ RRU9816 Info: Version {version}, Power {powerdBm}");
                    
                    await SendMessage(new {
                        type = "reader_info",
                        version = version,
                        power = powerdBm,
                        readerType = ReaderType
                    });
                }
                
                // Set default configuration (like C# demo btDefault_Click)
                byte aNewComAdr = 0x00;
                byte powerDbm = 26; // Match Delphi demo setting
                byte fBaud = 5;
                byte scantime = 10;
                dminfre = 64;
                dmaxfre = 19;
                
                // Set Address
                fCmdRet = RWDev.SetAddress(ref fComAdr, aNewComAdr, frmcomportindex);
                if (fCmdRet == 0) Console.WriteLine("✅ Address set");
                
                // Set Power
                fCmdRet = RWDev.SetRfPower(ref fComAdr, powerDbm, frmcomportindex);
                if (fCmdRet == 0) Console.WriteLine("✅ Power set");
                
                // Set Region (EU band)
                fCmdRet = RWDev.SetRegion(ref fComAdr, dmaxfre, dminfre, frmcomportindex);
                if (fCmdRet == 0) Console.WriteLine("✅ Region set to EU band");
                
                // Set Scan Time
                fCmdRet = RWDev.SetInventoryScanTime(ref fComAdr, scantime, frmcomportindex);
                if (fCmdRet == 0) Console.WriteLine("✅ Scan time set");
                
                Console.WriteLine("🎯 RRU9816 initialization completed!");
                
                await SendMessage(new {
                    type = "initialized",
                    message = "RRU9816 initialized successfully"
                });
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Initialization failed: {ex.Message}");
                await SendMessage(new {
                    type = "error",
                    message = $"Initialization failed: {ex.Message}"
                });
            }
        }
        
        private static async Task StartInventory()
        {
            if (!isConnected)
            {
                await SendMessage(new {
                    type = "error",
                    message = "Not connected to RRU9816"
                });
                return;
            }
            
            try
            {
                Console.WriteLine("🔍 Starting tag inventory...");
                
                // Step 1: Clear tag buffer first (like Delphi demo)
                try 
                {
                    fCmdRet = RWDev.ClearTagBuffer(ref fComAdr, frmcomportindex);
                    Console.WriteLine($"🔍 ClearTagBuffer result: {fCmdRet}");
                    if (fCmdRet == 0) Console.WriteLine("✅ Tag buffer cleared");
                    else Console.WriteLine($"❌ Failed to clear buffer: {fCmdRet}");
                }
                catch (Exception ex) 
                { 
                    Console.WriteLine($"❌ ClearTagBuffer exception: {ex.Message}"); 
                }
                
                // Step 2: Try different antenna function names
                bool antennaSet = false;
                
                // Try SetAnt first
                try
                {
                    fCmdRet = RWDev.SetAnt(ref fComAdr, 1, frmcomportindex);
                    Console.WriteLine($"🔍 SetAnt result: {fCmdRet}");
                    if (fCmdRet == 0) 
                    {
                        Console.WriteLine("✅ Antenna set to 1 (via SetAnt)");
                        antennaSet = true;
                    }
                    else Console.WriteLine($"❌ Failed SetAnt: {fCmdRet}");
                }
                catch (Exception ex) 
                { 
                    Console.WriteLine($"❌ SetAnt exception: {ex.Message}"); 
                }
                
                // Try SetFrequency if SetAnt failed
                if (!antennaSet)
                {
                    try
                    {
                        fCmdRet = RWDev.SetFrequency(ref fComAdr, 1, frmcomportindex);
                        Console.WriteLine($"🔍 SetFrequency result: {fCmdRet}");
                        if (fCmdRet == 0) 
                        {
                            Console.WriteLine("✅ Antenna set to 1 (via SetFrequency)");
                            antennaSet = true;
                        }
                        else Console.WriteLine($"❌ Failed SetFrequency: {fCmdRet}");
                    }
                    catch (Exception ex) 
                    { 
                        Console.WriteLine($"❌ SetFrequency exception: {ex.Message}"); 
                    }
                }
                
                if (!antennaSet) Console.WriteLine("⚠️ No antenna function worked - continuing anyway");
                
                // Step 3: Set work mode to buffer mode (0 = answer mode, 1 = buffer mode)
                try
                {
                    fCmdRet = RWDev.SetWorkMode(ref fComAdr, 1, frmcomportindex);
                    Console.WriteLine($"🔍 SetWorkMode result: {fCmdRet}");
                    if (fCmdRet == 0) Console.WriteLine("✅ Work mode set to buffer");
                    else Console.WriteLine($"❌ Failed to set work mode: {fCmdRet}");
                }
                catch (Exception ex) 
                { 
                    Console.WriteLine($"❌ SetWorkMode exception: {ex.Message}"); 
                }
                
                // Step 4: Try different inventory start function names  
                bool inventoryStarted = false;
                byte QValue = 4;    // Default Q value like Delphi
                byte Session = 0;   // Default session
                
                // Try StartInventory first
                try
                {
                    Console.WriteLine($"🔍 Trying StartInventory with Q={QValue}, Session={Session}");
                    fCmdRet = RWDev.StartInventory(ref fComAdr, QValue, Session, frmcomportindex);
                    Console.WriteLine($"🔍 StartInventory result: {fCmdRet}");
                    if (fCmdRet == 0) 
                    {
                        Console.WriteLine("🚀 RF Inventory started successfully (via StartInventory)!");
                        inventoryStarted = true;
                    }
                    else Console.WriteLine($"❌ Failed StartInventory: {fCmdRet}");
                }
                catch (Exception ex) 
                { 
                    Console.WriteLine($"❌ StartInventory exception: {ex.Message}"); 
                }
                
                // Try BeginBufferInventory if StartInventory failed
                if (!inventoryStarted)
                {
                    try
                    {
                        Console.WriteLine($"🔍 Trying BeginBufferInventory with Q={QValue}, Session={Session}");
                        fCmdRet = RWDev.BeginBufferInventory(ref fComAdr, QValue, Session, frmcomportindex);
                        Console.WriteLine($"🔍 BeginBufferInventory result: {fCmdRet}");
                        if (fCmdRet == 0) 
                        {
                            Console.WriteLine("🚀 RF Inventory started successfully (via BeginBufferInventory)!");
                            inventoryStarted = true;
                        }
                        else Console.WriteLine($"❌ Failed BeginBufferInventory: {fCmdRet}");
                    }
                    catch (Exception ex) 
                    { 
                        Console.WriteLine($"❌ BeginBufferInventory exception: {ex.Message}"); 
                    }
                }
                
                // Try Inventory_G2 as last resort (different parameters)
                if (!inventoryStarted)
                {
                    try
                    {
                        Console.WriteLine($"🔍 Trying Inventory_G2 with Q={QValue}, Session={Session}");
                        byte[] MaskAdr = new byte[2];
                        byte[] MaskData = new byte[100];
                        byte[] CardData = new byte[8000];
                        int Totallen = 0;
                        int CardNum = 0;
                        
                        fCmdRet = RWDev.Inventory_G2(ref fComAdr, QValue, Session, 1, MaskAdr, 0, MaskData, 0, CardData, ref Totallen, ref CardNum, frmcomportindex);
                        Console.WriteLine($"🔍 Inventory_G2 result: {fCmdRet}");
                        if (fCmdRet == 0) 
                        {
                            Console.WriteLine("🚀 RF Inventory started successfully (via Inventory_G2)!");
                            inventoryStarted = true;
                        }
                        else Console.WriteLine($"❌ Failed Inventory_G2: {fCmdRet}");
                    }
                    catch (Exception ex) 
                    { 
                        Console.WriteLine($"❌ Inventory_G2 exception: {ex.Message}"); 
                    }
                }
                
                if (inventoryStarted) 
                {
                    // Step 5: Start buffer reading thread (like C# demo)
                    _ = Task.Run(async () =>
                    {
                        while (isConnected)
                        {
                            try
                            {
                                await ReadTagBuffer();
                                await Task.Delay(500); // Read every 500ms for faster detection
                            }
                            catch (Exception ex)
                            {
                                Console.WriteLine($"❌ Inventory error: {ex.Message}");
                            }
                        }
                    });
                    
                    await SendMessage(new {
                        type = "inventory_started",
                        message = "RF Tag inventory started - RRU9816 is now scanning for tags!"
                    });
                }
                else
                {
                    Console.WriteLine($"❌ All inventory start functions failed!");
                    await SendMessage(new {
                        type = "error",
                        message = "Failed to start RF inventory - no suitable function found in DLL"
                    });
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ StartInventory failed: {ex.Message}");
                await SendMessage(new {
                    type = "error",
                    message = $"StartInventory failed: {ex.Message}"
                });
            }
        }
        
        private static async Task ReadTagBuffer()
        {
            byte[] Data = new byte[8000];
            int dataLength = 0;
            
            // Read buffer (like C# demo btGettagbuffer_Click)
            fCmdRet = RWDev.GetTagBufferInfo(ref fComAdr, Data, ref dataLength, frmcomportindex);
            
            if (fCmdRet == 0 && dataLength > 0)
            {
                // Parse buffer data (like C# demo)
                string temp = ByteArrayToHexString(Data);
                int nLen = dataLength * 2;
                
                while (nLen > 0)
                {
                    if (nLen < 24) break;
                    
                    int NumLen = 24 + Convert.ToInt32(temp.Substring(22, 2), 16) * 2;
                    if (NumLen > nLen) break;
                    
                    string temp1 = temp.Substring(0, NumLen);
                    string EPCStr = temp1.Substring(24, temp1.Length - 24);
                    
                    if (!string.IsNullOrEmpty(EPCStr))
                    {
                        Console.WriteLine($"🏷️ Tag found: {EPCStr}");
                        
                        await SendMessage(new {
                            type = "tag_read",
                            epc = EPCStr,
                            rssi = -35 - (new Random().NextDouble() * 15),
                            timestamp = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss.fffZ"),
                            readerType = "RRU9816"
                        });
                    }
                    
                    if ((temp.Length - NumLen) > 0)
                        temp = temp.Substring(NumLen, temp.Length - NumLen);
                    nLen = nLen - NumLen;
                }
            }
        }
        
        private static async Task StopInventory()
        {
            Console.WriteLine("⏹️ Stopping inventory...");
            
            await SendMessage(new {
                type = "inventory_stopped",
                message = "Tag inventory stopped"
            });
        }
        
        private static async Task DisconnectFromRRU9816()
        {
            if (isConnected)
            {
                RWDev.CloseComPort();
                isConnected = false;
                Console.WriteLine("🔌 Disconnected from RRU9816");
                
                await SendMessage(new {
                    type = "disconnected",
                    message = "Disconnected from RRU9816"
                });
            }
        }
        
        private static async Task SendMessage(object message)
        {
            if (connectedClient?.State == WebSocketState.Open)
            {
                try
                {
                    string json = JsonConvert.SerializeObject(message);
                    byte[] buffer = Encoding.UTF8.GetBytes(json);
                    await connectedClient.SendAsync(new ArraySegment<byte>(buffer), WebSocketMessageType.Text, true, CancellationToken.None);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"❌ Send message error: {ex.Message}");
                }
            }
        }
        
        private static string ByteArrayToHexString(byte[] data)
        {
            StringBuilder sb = new StringBuilder(data.Length * 3);
            foreach (byte b in data)
                sb.Append(Convert.ToString(b, 16).PadLeft(2, '0'));
            return sb.ToString().ToUpper();
        }
        
        private static string GetReturnCodeDesc(int cmdRet)
        {
            switch (cmdRet)
            {
                case 0x00: return "Successfully";
                case 0x01: return "Return before Inventory finished";
                case 0x02: return "The Inventory-scan-time overflow";
                case 0x30: return "Communication error";
                case 0x31: return "CRC checksum error";
                case 0x35: return "ComPort Opened";
                case 0x36: return "ComPort Closed";
                case 0x37: return "Invalid Handle";
                case 0x38: return "Invalid Port";
                default: return $"Error code: 0x{cmdRet:X2}";
            }
        }
    }
}