import sys
import numpy as np
from struct import *
import pdb
import crcmod


def remap(x : np.ndarray, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


'''
https://www.eevblog.com/forum/testgear/rigol-dg1000z-raf-file-format/
You can use a standard CRC-16/CCITT-FALSE algorithm mentioned in the following link 
and XOR the output with 0x0069 or you can just use 0x1021 for the polynomial and 
0xebcc for the intial value instead of the default values.

The waveform CRC input data starts at byte 57 and runs to the end of the file
The header waveform is bytes 1 to 50. You have to calculate the waveform CRC first 
and place it in the header before you calculate the header CRC.

// check = 0x6809 residue = 0x0000 name = "CRC-16/RIGOL 2"
0x1021, 0xEBCC, 0, false, false
'''

'''
https://stackoverflow.com/questions/35205702/calculating-crc16-in-python
CRC-16/CCITT-FALSE
'''
# def crc16(data : bytearray, offset , length):
#     if data is None or offset < 0 or offset > len(data)- 1 and offset+length > len(data):
#         return 0
#     crc = 0xEBCC # 0xFFFF
#     for i in range(0, length):
#         crc ^= data[offset + i] << 8
#         for j in range(0,8):
#             if (crc & 0x8000) > 0:
#                 crc =(crc << 1) ^ 0x1021
#             else:
#                 crc = crc << 1
#     return crc & 0xFFFF

def crc16(data : bytearray, offset , length):
    c = crcmod.predefined.Crc('xmodem')
    c = crcmod.mkCrcFun(0x11021, 0xEBCC, False, 0x0000)
    return c(data)


def read_raf(input):
    if input is None:
        return None
    elif isinstance(input, str):
        with open(input,"rb") as f:
            data = f.read()
    elif isinstance(input, np.ndarray):
        data = input
    head_fmt = '<L ? ? ? 25s q l l H H 4x'
    hdr_size = calcsize(head_fmt)
    L,b1,b2,FsMode,Filename,Fs,HiV,LowV,DataCRC,HeaderCRC = unpack_from(head_fmt, data)
    waveform = unpack_from('<{}H'.format(L), data, hdr_size)
    header = np.array(unpack_from('<50B', data, 0), dtype=np.uint8)
    x = np.array(waveform, dtype=np.int16)
    HiV /= 10**7
    LowV /= 10**7
    Filename = Filename.decode("utf-8")
    # Range from 0, ..., 8192, ..., 16383
    # Shift to -8191, ..., 0, ..., 8191
    xv = x - 8191
    xv = remap(xv, -8191, 8191, LowV, HiV)
    crc_data = crc16(x.tobytes(), 0, 8192*2)
    crc_head = crc16(header.tobytes(), 0, 50)
    # Check CRC's match
    crc_data == DataCRC
    crc_head == HeaderCRC
    if FsMode:
        Fs *= 10**6
    else:
        Fs = 10.**6/Fs
    print('{} read in with {} samples at {} Hz'.format(Filename, len(xv), Fs))
    return xv, Fs, HiV, LowV


def write_raf(filename : str, data : np.ndarray, fs_Hz, LowV, HiV):
    data_u16 = (remap(data, LowV, HiV, -8191, 8191) + 8191).astype(np.uint16)
    L = len(data_u16)
    crc_data = crc16(data_u16.tobytes(), 0, L*2)
    phead_fmt = '<L ? ? ? 25s q l l H'
    ## Period Mode
    # FsMode = False
    # Fs = int(1./fs_Hz * 10**10)
    ## Freq Mode
    FsMode = True
    Fs = int(fs_Hz * 10**6)
    # Limit filename to 25 characters
    if len(filename) > 25:
        filename = filename[:25]
        print('Truncated filename to {}'.format(filename))
    # Extend to 25 characters if needed
    fname = filename + '\x00'*(25-len(filename))
    HiV = int(HiV * 10**7)
    LowV = int(LowV * 10**7)
    header = pack(phead_fmt, L, True, False, FsMode, fname.encode('utf-8'), Fs, HiV, LowV, crc_data)
    crc_head = crc16(header, 0, 50)
    header += pack('<Hl', crc_head, 0)
    bin_data = header + data_u16.tobytes()
    f = open(filename, 'wb')
    f.write(bin_data)
    f.close()
    print('{} wrote in with {} samples at {} Hz'.format(filename, len(data_u16), Fs/10.**6))

def main():
    try:
        print('main')
        xv, fs_Hz, HiV, LowV = read_raf('arb.raf')
        
        fs_Hz = 480000.
        t = np.arange(0., 10000.e3, 1.)/fs_Hz
        xv = np.pi*np.sin(2*np.pi*1000.*t)
        LowV = -3.14
        HiV = 3.14
        write_raf('write_test.raf', xv, fs_Hz, LowV, HiV)

        return False
    except ValueError as ve:
        return str(ve)


if __name__ == '__main__':
    # np.random.seed(1)
    # vals = (np.random.rand(100,)*100).astype(np.uint8)
    # print(hex(crc16(vals.tobytes(), 0, len(vals))))

    # c = crcmod.predefined.Crc('xmodem')
    # c = crcmod.mkCrcFun(0x11021, 0xEBCC, False, 0x0000)
    # print(hex(c(vals)))

    sys.exit(main())  # next section explains the use of sys.exit
