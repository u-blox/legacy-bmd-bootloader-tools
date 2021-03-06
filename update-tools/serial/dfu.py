#!/usr/bin/python

from collections import namedtuple
import binascii
import os
import sys
import re
import argparse
import serial
import time
import datetime
import tempfile
import subprocess
import platform
from enum import IntEnum
from struct import *

verbose = 0
checkBootloaderVersion = False

class Serial_Op_Code(IntEnum):
    Start            = 1
    Init             = 2
    Image_Xfer       = 3
    Validate         = 4
    Activate_N_Reset = 5
    Reset            = 6
    Config           = 9
    InitPatch        = 10
    Patch_Xfer       = 11
    Response         = 16

class Serial_Op_Status(IntEnum):
    Success             = 1
    Invalid_State_Err   = 2
    Not_Supported_Err   = 3
    Data_Sz_Err         = 4
    CRC_Err             = 5
    Op_Failed_Err       = 6
    Success_Need_Addl_Data = 7


def printVerbose(verbosity,outString):
    global verbose
    if verbosity <= verbose:
        print(outString)

def prettyHexString(inBytes,group=2,sep=' '):
    temp = binascii.hexlify(bytes(inBytes)).decode("utf-8").upper()

    #split every N chars with seperator
    out = sep.join(temp[i:i+group] for i in range(0, len(temp), group))
    return out

def printResult(verbosity,result):
    if(result == True):
        printVerbose(verbosity,"Success")
    else:
        printVerbose(verbosity,"Fail")

    return result

#error handler
def errorHandler(errString):
    print('Error: ' + errString)
    sys.exit(1)

def verifyVersion(version):
    printVerbose(5, 'Verify RigDFU version')
    if not (version.find("3.2.1") == -1):
        errorHandler('RigDFU v3.2.1 cannot be updated as a direct bootloader update. See Errata information in Release Notes.')

#check hex string
def parseHexString(inputString, numBytes):
    if isinstance(inputString, str):
        out = inputString.lower()
        out = re.sub(r'[^a-f0-9]', "" , out)

        if(len(out) == (2*numBytes)):
            return out
        else:
            errorHandler("invalid hex string: " + inputString)
    else:
        return None

def openSerial(portId,baud):
    try:
        connected = False
        #non-blocking mode
        sp = serial.Serial(portId,baud,rtscts=False,timeout=0)

        #activate bootloader
        time.sleep(2)
        printVerbose(0,"\nActivating RigDFU2 serial loader...")
        for i in range(8):
            sp.write((0xca, 0x9d, 0xc6, 0xa4))

            #exp reply of "x.x.x (xx)\r\n"
            rx = rxPacket(sp,37,timeout_s=0.5,silentFail=True,rawBytes=True)

            if(rx==None):
                printVerbose(0,"openSerial - No response from RigDFU, retrying...")
            else:
                version = rx.decode("ascii").strip()
                printVerbose(0,version)
                if checkBootloaderVersion:
                    verifyVersion(version)
                connected = True
                break

        if connected == True:
            return sp
        else:
            sp.close()
            errorHandler("openSerial - No response from RigDFU")
            return None
    except Exception as e:
        print(str(e))
        errorHandler("openSerial - RigDFU initialization error")

def txPacket(serialPort,opCode,txData):
    if(serialPort.isOpen() == False):
        errorHandler("txPacket - invalid Serial object")

    serialPort.flush()

    if(txData == None or len(txData) <= 253):
        txBytes = bytearray()

        #put start byte
        txBytes.append(0xAA)

        #put length (+1 for opcode)
        if(txData == None):
            txBytes.append(2)
        else:
            length = (len(txData) + 2)
            #special chars
            if length == 0xAA:
                txBytes.append(0xAB)
                txBytes.append(0xAC)
            elif length == 0xAB:
                txBytes.append(0xAB)
                txBytes.append(0xAB)
            else:
                txBytes.append(length)

        #op code
        txBytes.append(opCode)

        #add the data
        if txData != None:
            for b in txData:
                #special chars
                if b == 0xAA:
                    txBytes.append(0xAB)
                    txBytes.append(0xAC)
                elif b == 0xAB:
                    txBytes.append(0xAB)
                    txBytes.append(0xAB)
                else:
                    txBytes.append(b)

        printVerbose(2,"<"+prettyHexString(txBytes))
        serialPort.write(txBytes)
    else:
        errorHandler("txPacket - illegal data length {} > 254 bytes".format(len(txBytes)))

def rxPacket(serialPort,length,timeout_s=1,silentFail=False,rawBytes=False):
    if(serialPort.isOpen == False):
        return None

    start_time = datetime.datetime.now()
    rx_msg = bytearray()
    escape_cnt = 0
    escape = False;

    while( len(rx_msg) < (length+escape_cnt) and (datetime.datetime.now() - start_time).total_seconds() <= timeout_s ):
        
        byte = serialPort.read()

        if len(byte)!= 0:
            #raw read, just return the raw bytes...
            if rawBytes == True:
                rx_msg += byte
            #un-escape bytes and read more if we need to...
            else:
                if escape == False and byte == 0xAB:
                    escape = True
                    escape_cnt += 1
                elif escape == True:
                    if byte == 0xAB:
                        rx_msg += 0xAB
                    elif byte == 0xAC: 
                        rx_msg += 0xAA
                    else:
                        errorHandler("illegal escaped char: " + hex(byte))
                    escape = False
                else:
                    rx_msg += byte


    if(len(rx_msg) != length):
        #determine packet or ascii
        msgString = ""
        if len(rx_msg) != 0 and rx_msg[0] == 0xAA:
            msgString = prettyHexString(rx_msg)
        else:
            msgString = rx_msg.decode("utf-8")
        
        if silentFail == True:
            rx_msg = None
        else:
            errorHandler("rxPacket - unexpected msg length {}/{}, msg: {}".format(len(rx_msg),length,msgString))
    else:
        printVerbose(2,">"+prettyHexString(rx_msg))

    return rx_msg

def rxOpResponse(serialPort,opCode,expOpStatus=Serial_Op_Status.Success,timeout_s=10):
    result = False

    #first read 5 bytes
    rx = rxPacket(serialPort,5,timeout_s)

    #check the length and start byte
    if(rx != None and len(rx) == 5 and rx[0] == 0xAA):
        expLen          = rx[1]
        rxOpCode        = rx[2]
        rxPayloadOpCode = rx[3]
        rxPayloadStatus = rx[4]

        if expLen != 4:
            printVerbose(1,"unexpected response length {}/{}".format(expLen,4))
        elif rxOpCode != Serial_Op_Code.Response:
            printVerbose(1,"unexpected response opcode {}/{}".format(rxOpCode,Serial_Op_Code.Response))
        elif rxPayloadOpCode != opCode:
            printVerbose(1,"unexpected opcode {}/{}".format(rxPayloadOpCode,opCode))
        elif rxPayloadStatus != expOpStatus:
            printVerbose(1,"unexpected opstatus {}/{}".format(rxPayloadStatus,expOpStatus))
        else:
            printVerbose(1,"rxOpResponse OK - op {}, status {}".format(opCode,expOpStatus))
            result = True;

    return result

def buildConfigPacket(mac,oldkey,newkey):

    if(len(mac) != 6 or len(oldkey) != 16 or len(oldkey) != 16):
        errorHandler("invalid config packet arguments!")

    allzeros = bytearray()
    allff = bytearray()
    for i in range(0, 16):
        allzeros.append(0x00)
        allff.append(0xFF)

    configPkt = bytearray()
    #reuse signimage to encrypt...
    #sign image expects
    #uint32_t[3] - metadata lengths (sd,bl,app), we can use any region
    #uint8_t[16] - crypto iv placeholder
    #uint8_t[16] - crypto tag placeholder
    #uint8_t[N]  - N-bytes to be encrypted (N is sum of the metadata lengths)

    configPkt.append(48) #config data is 48 bytes
    configPkt.extend([0]*11) #remaining metadata is zeroes
    configPkt.extend([0]*(16+16)) #cryptotag/iv placeholder

    #config data 48 bytes
    configPkt.extend(bytes(oldkey)) #16 bytes
    configPkt.extend(bytes(newkey)) #16 bytes
    configPkt.extend(bytes(mac))    #6 bytes
    configPkt.extend([0]*10)        #10 bytes

    printVerbose(1, "\nconfigPkt (plaintext):\n" + prettyHexString(configPkt))

    if set(oldkey) == set(allzeros) or set(oldkey) == set(allff):
        return configPkt

    #save temp files in directory
    tmpDir = tempfile.mkdtemp(dir=os.getcwd())
    plainTxtPath = os.path.join(tmpDir,"pt.bin")
    cipherTxtPath = os.path.join(tmpDir,"ct.bin")

    #write the plaintext out so the external tool can encrypt it
    f = open(plainTxtPath, "wb")
    f.write(configPkt)
    f.close()

    #run the ext tool
    system_type = platform.system()
    signimagepath = ""
    if(system_type == "Windows"):
        is_64bits = sys.maxsize > 2**32
        if(is_64bits):
            signimagepath = "..\..\image-tools\signimage\signimage-w64.exe"
        else:
            signimagepath = "..\..\image-tools\signimage\signimage-w32.exe"
    elif(system_type == "Darwin"):
        signimagepath = "../../image-tools/signimage/signimage-osx"
    elif(system_type == "Linux"):
        signimagepath = "../../image-tools/signimage/signimage-linux"
    else:
        sys.exit("Unknown system")
		
    if subprocess.call([signimagepath, plainTxtPath, cipherTxtPath, prettyHexString(oldkey,sep='')]) != 0:
        errorHandler("Configuration encryption failed")

    #readback encrypted
    f = open(cipherTxtPath,"rb")
    cryptoPkt = f.read()
    f.close()

    printVerbose(1, "\nconfigPkt (ciphertext):\n"+ prettyHexString(cryptoPkt))

    #cleanup
    os.remove(cipherTxtPath)
    os.remove(plainTxtPath)
    os.rmdir(tmpDir)

    printVerbose(1, "Configuration encryption success")

    return cryptoPkt

def doConfig(mac,oldkey,newkey):    
    printVerbose(1,"\nOpen serial port: {} baud: {}".format(args.serial, args.baud))
    serialPort = openSerial(args.serial,args.baud)

    #build and encrypt config packet
    configPkt = buildConfigPacket(mac,oldkey,newkey)
    
    #check the packet length
    if(len(configPkt) != 92):
        errorHandler("doConfig - illegal configPkt length {}/{}".format(len(configPkt),92))

    printVerbose(0, "\nConfiguring device...")
    txPacket(serialPort,Serial_Op_Code.Config,configPkt)
    printResult(0,rxOpResponse(serialPort,Serial_Op_Code.Config,timeout_s=5))

    printVerbose(0, "Configuration complete!")


def doDFU(startPkt,initPkt,imageBin):
    printVerbose(0,"\nOpen serial port: {} baud: {}".format(args.serial, args.baud))
    serialPort = openSerial(args.serial,args.baud)

    #start message
    printVerbose(0,"\nStarting DFU...")
    startDFU(serialPort,startPkt)

    #init message
    printVerbose(0,"\nIniting DFU...")
    initDFU(serialPort,initPkt)

    #image transfer
    printVerbose(0,"\nUploading image...")
    xferimageDFU(serialPort,imageBin)

    #image transfer
    printVerbose(0,"\nValidating image...")
    validateDFU(serialPort)

    #image transfer
    printVerbose(0,"\nActivating image...")
    activateNresetDFU(serialPort)

    printVerbose(0,"\nWaiting for activation...")
    time.sleep(1)

    printVerbose(0,"\nDFU Complete!")
    return True

def doDFUPatch(startPkt, initPkt, initPatchPkt, patchBin):
    result = False

    printVerbose(0,"\nOpen serial port: {} baud: {}".format(args.serial, args.baud))
    serialPort = openSerial(args.serial,args.baud)

    #start message
    printVerbose(0,"\nStarting DFU...")
    result = startDFU(serialPort,startPkt)

    if not result:
        printVerbose(0, "\nStart DFU Failed")
        return

    #init message
    printVerbose(0,"\nInitializing DFU...")
    result = initDFU(serialPort,initPkt)

    if not result:
        printVerbose(0, "\nStart DFU Failed")
        return

    #init patch message
    printVerbose(0,"\nInitializing Patch...")
    result = initPatch(serialPort, initPatchPkt)

    if not result:
        printVerbose(0, "\nStart DFU Failed")
        return

    #patch transfer
    printVerbose(0,"\nUploading image...")
    result = xferPatchImageDFU(serialPort, patchBin)

    if not result:
        printVerbose(0, "\nStart DFU Failed")
        return

    #image validation
    printVerbose(0,"\nValidating image...")
    result = validateDFU(serialPort)

    if not result:
        printVerbose(0, "\nStart DFU Failed")
        return

    #image activation
    printVerbose(0,"\nActivating image...")
    result = activateNresetDFU(serialPort)

    if not result:
        printVerbose(0, "\nStart DFU Failed")
        return

    printVerbose(0,"\nWaiting for activation...")
    time.sleep(1)

    printVerbose(0,"\nDFU Complete!")
    return True

def startDFU(serialPort,startPkt):
    result = False

    if(len(startPkt) == 12):
        txPacket(serialPort,Serial_Op_Code.Start,startPkt)
        result = printResult(0,rxOpResponse(serialPort,Serial_Op_Code.Start,timeout_s=5))
        time.sleep(.5)
    else:
        errorHandler("invalid startPkt length {} != 12".format(len(startPkt)))    

    return result

def initDFU(serialPort,initPkt):
    result = False

    if(len(initPkt) == 32):
        txPacket(serialPort,Serial_Op_Code.Init,initPkt)
        result = printResult(0,rxOpResponse(serialPort,Serial_Op_Code.Init,timeout_s=10))
    else:
        errorHandler("invalid initPkt length {} != 32".format(len(initPkt)))    

    return result

def initPatch(serialPort,initPatchPkt):
    result = False

    if(len(initPatchPkt) == 12):
        txPacket(serialPort,Serial_Op_Code.InitPatch,initPatchPkt)
        result = printResult(0,rxOpResponse(serialPort,Serial_Op_Code.InitPatch,timeout_s=5))
    else:
        errorHandler("invalid initPkt length {} != 32".format(len(initPkt)))    

    return result

def xferimageDFU(serialPort,imageBinary,chunkSz=192):
    result = True
    imageTotalSz = len(imageBinary)
    notifyChunkSz = 2048
    notifySz = notifyChunkSz
    offset = 0

    while(offset < imageTotalSz):
        curChunkSz = min(chunkSz,(imageTotalSz-offset))
        txBytes = imageBinary[offset:(offset+curChunkSz)]
        offset += curChunkSz

        txPacket(serialPort,Serial_Op_Code.Image_Xfer,txBytes)

        if offset != imageTotalSz:
            result &= rxOpResponse(serialPort,Serial_Op_Code.Image_Xfer,Serial_Op_Status.Success_Need_Addl_Data);
        else:
            result &= rxOpResponse(serialPort,Serial_Op_Code.Image_Xfer,Serial_Op_Status.Success)

        #notify progress
        if(offset >= notifySz or offset == imageTotalSz):
            notifySz += notifyChunkSz
            printVerbose(0,"xfered {}/{} bytes".format(offset, imageTotalSz))

    printResult(0,result)
    return result

def xferPatchImageDFU(serialPort,patchBinary,chunkSz=192):
    result = True
    imageTotalSz = len(patchBinary)
    offset = 0

    while(offset < imageTotalSz):
        curChunkSz = min(chunkSz,(imageTotalSz-offset))
        txBytes = patchBinary[offset:(offset+curChunkSz)]
        offset += curChunkSz

        txPacket(serialPort,Serial_Op_Code.Patch_Xfer,txBytes)

        if offset != imageTotalSz:
            result &= rxOpResponse(serialPort,Serial_Op_Code.Patch_Xfer, Serial_Op_Status.Success_Need_Addl_Data)
        else:
            result &= rxOpResponse(serialPort, Serial_Op_Code.Patch_Xfer, Serial_Op_Status.Success)
        
        printVerbose(0,"xfered {}/{} bytes".format(offset, imageTotalSz))
  
    printResult(0,result)
    return result

def validateDFU(serialPort):
    txPacket(serialPort,Serial_Op_Code.Validate,None)
    return printResult(0,rxOpResponse(serialPort,Serial_Op_Code.Validate,timeout_s=5))

def activateNresetDFU(serialPort):
    txPacket(serialPort,Serial_Op_Code.Activate_N_Reset,None)
    return printResult(0,rxOpResponse(serialPort,Serial_Op_Code.Activate_N_Reset,timeout_s=5))

#dfu data
parser = argparse.ArgumentParser(description="RigDFU2 Serial Updater")
parser.add_argument("-M",   "--newmac", type=str, help="new MAC address (6 octets, big-endian)")
parser.add_argument("-K",   "--newkey", type=str, help="new key (16 bytes, big-endian)")
parser.add_argument("-k",   "--oldkey", type=str, help="old key (16 bytes, big-endian)")
parser.add_argument("-s",   "--serial", type=str, help="serial port")
parser.add_argument("-b",   "--baud",   type=int, help="serial baudrate [115200]", default=115200)
parser.add_argument("-p",   "--patch", action="store_true", help="set when sending a patch file")
parser.add_argument("-i",   "--infile", type=str, help="packed data binary file to upload")
parser.add_argument("-v",   "--verbose", action="store_true", help="enable verbose level 1")
parser.add_argument("-vv",  "--vverbose", type=int, help="set verbose level (1,2)", default=0)
args = parser.parse_args()

if(args.serial == None):
   errorHandler("serial port must be specified with -s/--serial.")

#set verbose
if args.vverbose != 0:
    verbose = args.vverbose
elif args.verbose == True:
    verbose = 1
else:
    verbose = 0

if verbose != 0:
    printVerbose(0,"verbose output level {}".format(verbose))
    

#config mode?
if(args.newmac != None or args.newkey != None or args.oldkey != None):
    printVerbose(0,"\nConfiguring DFU...")

    if(args.oldkey == None):
        errorHandler("--oldkey/-k must be specified when using --newkey/K or --mac/-M")
    elif(args.newmac == None and args.newkey == None):
        errorHandler("no operation specified, pass --newkey/K or --mac/-M with --oldkey/-k")

    #clean all the inputs
    args.newmac = parseHexString(args.newmac, 6)
    args.newkey = parseHexString(args.newkey, 16)
    args.oldkey = parseHexString(args.oldkey, 16)

    mac = [0] * 6
    newkey = [0] * 16 
    oldkey = [0] * 16

    #parse to bytes
    if args.newmac:
        mac     = binascii.a2b_hex(args.newmac)[::-1]

    if args.newkey:
        newkey  = binascii.a2b_hex(args.newkey)

    if args.oldkey:
        oldkey  = binascii.a2b_hex(args.oldkey)

    printVerbose(0, "mac: " + prettyHexString(mac))
    printVerbose(0, "newkey: " + prettyHexString(newkey))
    printVerbose(0, "oldkey: " + prettyHexString(oldkey))

    #we made it, ok lets proceed...
    doConfig(mac,oldkey,newkey)

#dfu update?
elif(args.infile != None):
    printVerbose(0,"\nUploading firmware to DFU...")

    #check validity
    if(os.path.exists(args.infile) != True):
        errorHandler("Invalid input file specified: " + args.infile)

    #read the file in
    fd = open(args.infile, "rb")
    bindata = fd.read()
    fd.close()
    printVerbose(1,"\nRead {} bytes from file: {}".format(len(bindata),args.infile))

    #prepare to unpack
    StartPkt        = namedtuple('StartPkt', 'sd bl app')
    InitPkt         = namedtuple('InitPkt', 'iv tag')
    PatchInitPkt    = namedtuple('PatchInitPkt', 'len crc oldcrc')

    def extractBytes(buffer, start, end=None):
        result = None

        if end == None:
            print("{0} - end".format(start))
            result = buffer[start:]
        else:
            print("{0} - {1}".format(start, end))
            result = buffer[start:end]
        return result

    def has_patch_key(byte_array):

        patch_key = [0xac, 0xb3, 0x37, 0xe8, 0xd0, 0xeb, 0x40, 0x90,
                     0xa4, 0xf3, 0xbb, 0x85, 0x7a, 0x5b, 0x2a, 0xf6]
        byte_array_list = list(byte_array)

        result = False

        if patch_key == byte_array_list:
            result = True
        
        return result

    patch_key_size = 16
    start_packet_size = 12
    init_packet_size = 32
    patch_init_packet_size = 12

    #unpack
    try:

        #raw binary
        if args.patch == True or has_patch_key(bindata[:patch_key_size]):

            patch_key_start         = 0
            start_packet_start      = patch_key_start + patch_key_size
            init_packet_start       = start_packet_start + start_packet_size
            patch_init_packet_start = init_packet_start + init_packet_size
            image_bin_start         = patch_init_packet_start + patch_init_packet_size

            patchKeyBin  = bindata[patch_key_start:start_packet_start]
            startBin     = bindata[start_packet_start:init_packet_start]
            initBin      = bindata[init_packet_start:patch_init_packet_start]
            patchInitBin = bindata[patch_init_packet_start:image_bin_start]
            imageBin     = bindata[image_bin_start:]

            args.patch = True

        else:  
            start_packet_start = 0
            init_packet_start  = start_packet_start + start_packet_size
            image_bin_start    = init_packet_start + init_packet_size
            
            startBin = bindata[start_packet_start:init_packet_start]
            initBin  = bindata[init_packet_start:image_bin_start]
            imageBin = bindata[image_bin_start:]

        #parse to struct
        startPkt    = StartPkt._make(unpack('<LLL', startBin))
        initPkt     = InitPkt._make((initBin[:16], initBin[16:]))

        if(args.patch):
            patchInitPkt = PatchInitPkt._make(unpack('<LLL', patchInitBin))

        printVerbose(1, "startPkt: " + prettyHexString(startBin))
        printVerbose(1, "cryptoIV: "  + prettyHexString(initPkt.iv))
        printVerbose(1, "cryptoTag: " + prettyHexString(initPkt.tag))
        if(args.patch):
            printVerbose(1, "patchInitPkt: " + prettyHexString(patchInitBin))

    except:
        errorHandler("Unexpected binary file format!")

    printVerbose(0,"\nImage Data:\n\tsoftdevice: {}\n\tbootloader: {}\n\tapplication: {}\n\tbinarySize: {}".format(startPkt.sd, startPkt.bl, startPkt.app, len(imageBin)))

    #sanity checks
    if(startPkt.sd == 0 and startPkt.bl == 0 and startPkt.app == 0):
        errorHandler("sizes are all 0, no data to send.")

    if((startPkt.sd % 4) or (startPkt.bl % 4) or (startPkt.app % 4)):
        errorHandler("sizes must be a multiple of 4")

    if (startPkt.app and (startPkt.sd or startPkt.bl)):
        errorHandler("application must be sent by itself")

    if (args.patch and (startPkt.sd or startPkt.bl)):
        errorHandler("only application can be patched")

    if(not args.patch):
        if ((startPkt.sd + startPkt.bl + startPkt.app) != len(imageBin)):
            errorHandler("total image length {} doesn't match expected {}".format(len(imageBin), (sizes.sd + sizes.bl + sizes.app)))
    
    if(args.patch):
        if (patchInitPkt.len != len(imageBin)):
            errorHandler("not enough patch data is present")

        if (patchInitPkt.crc == 0 or patchInitPkt.oldcrc == 0):
            errorHandler("both crc values must be present in the patch")

    if(startPkt.sd or startPkt.bl):
        checkBootloaderVersion = True

    if(args.patch):
        doDFUPatch(startBin,initBin,patchInitBin,imageBin)
    else:
        doDFU(startBin,initBin,imageBin)
else:
    errorHandler("Input binary file must be specified with -i/--infile.")

