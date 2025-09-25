using System;
using System.Runtime.InteropServices;

namespace UHF
{
    public static class RWDev
    {
        private const string DLLNAME = @"RRU9816.dll";

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int OpenComPort(int Port,
                                             ref byte ComAddr,
                                             byte Baud,
                                             ref int PortHandle);

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int CloseComPort();

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int GetReaderInformation(ref byte ComAdr,
                                                      byte[] VersionInfo,
                                                      ref byte ReaderType,
                                                      ref byte TrType,
                                                      ref byte dmaxfre,
                                                      ref byte dminfre,
                                                      ref byte powerdBm,
                                                      ref byte ScanTime,
                                                      ref byte Ant,
                                                      ref byte BeepEn,
                                                      ref byte OutputRep,
                                                      ref byte CheckAnt,
                                                      int FrmHandle);

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int SetRegion(ref byte ComAdr,
                                           byte dmaxfre,
                                           byte dminfre,
                                           int frmComPortindex);

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int SetAddress(ref byte ComAdr,
                                            byte ComAdrData,
                                            int frmComPortindex);

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int SetInventoryScanTime(ref byte ComAdr,
                                                      byte ScanTime,
                                                      int frmComPortindex);

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int SetBaudRate(ref byte ComAdr,
                                            byte baud,
                                            int frmComPortindex);

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int SetRfPower(ref byte ComAdr,
                                            byte powerDbm,
                                            int frmComPortindex);

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int GetTagBufferInfo(ref byte ComAdr,
                                                  byte[] Data,
                                                  ref int dataLength,
                                                  int frmComPortindex);

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int ClearTagBuffer(ref byte ComAdr,
                                               int frmComPortindex);

        // Try different function names that might exist in RRU9816.dll
        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int Inventory_G2(ref byte ComAdr,
                                              byte QValue,
                                              byte Session, 
                                              byte MaskMem,
                                              byte[] MaskAdr,
                                              byte MaskLen,
                                              byte[] MaskData,
                                              byte MaskDataLen,
                                              byte[] CardData,
                                              ref int Totallen,
                                              ref int CardNum,
                                              int frmComPortindex);

        // Try alternative inventory start function names
        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int StartInventory(ref byte ComAdr,
                                               byte QValue,
                                               byte Session,
                                               int frmComPortindex);

        // Try buffer-specific inventory  
        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int BeginBufferInventory(ref byte ComAdr,
                                                      byte QValue,
                                                      byte Session,
                                                      int frmComPortindex);

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int StopInventory(ref byte ComAdr,
                                              int frmComPortindex);

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int SetWorkMode(ref byte ComAdr,
                                            byte WorkMode,
                                            int frmComPortindex);

        // Try alternative antenna function names
        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int SetFrequency(ref byte ComAdr,
                                             byte AntennaNo,
                                             int frmComPortindex);

        [DllImport(DLLNAME, CallingConvention = CallingConvention.StdCall)]
        public static extern int SetAnt(ref byte ComAdr,
                                       byte AntennaNo,
                                       int frmComPortindex);
    }
}