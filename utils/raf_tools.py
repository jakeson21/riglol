import argparse
import sys
import numpy as np
from struct import *
import pdb
import crcmod
import pyvisa
import time
import math
import json


def remap(x: np.ndarray, in_min, in_max, out_min, out_max):
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

https://stackoverflow.com/questions/35205702/calculating-crc16-in-python
CRC-16/CCITT-FALSE
'''


def to_dac_values(values: np.ndarray, low_v: float, high_v: float):
    """ Range from 0, ..., 8192, ..., 16383
        Shift to max_neg [low_v], ..., 0, ..., max_pos [high_v]
    """
    return remap(values, low_v, high_v, 0, 16383).astype(np.uint16)


def from_dac_values(dac: np.ndarray, low_v: float, high_v: float):
    """ Range from max_neg [low_v], ..., 0, ..., max_pos [high_v]
        Shift to 0, ..., 8192, ..., 16383
    """
    return remap(dac, 0., 16383., low_v, high_v)


def open_device(device):
    # Can specify a resource index, string, or device handle
    res = pyvisa.ResourceManager()
    if isinstance(device, int):
        device = res.open_resource(res.list_resources()[device])
    elif isinstance(device, str):
        device = res.open_resource(device)
    elif isinstance(device, pyvisa.resources.usb.USBInstrument) or isinstance(device, pyvisa.resources.usb.USBInstrument):
        print('Device handle already acquired')
    else:
        print('Unknown device type specified')
        return False
    return device, res


def send_file_to_arb(path: str = 'square.raf', device=None, channel: int = 1):
    dac = read_raf(path, dac_values=True)
    if dac is not None:
        send_data_to_arb(**dac, channel=channel, device=device)
    else:
        print('Failed to read in file\n')


def send_data_to_arb(samples: np.ndarray,
                     fs: float,
                     high_v: float = 1.0,
                     low_v: float = -1.0,
                     channel: int = 1,
                     device=0):
    if low_v >= high_v:
        print('low_v must be < high_v')
        return False
    if samples.dtype is not np.dtype('uint16'):
        print('Converting samples to uint16\n')
        samples = to_dac_values(samples, low_v, high_v)

    # Can specify a resource index, string, or device handle
    device, rm = open_device(device=device)
    device.timeout = 2000
    device.write_termination = '\n'

    print('Device:', device.query("*IDN?"))
    print('16M Option:', device.query('*OPT?').rstrip())
    device.write(':SYSTem:BEEPer')
    print(device.query('*OPC?').rstrip())
    device.write(':OUTP{} OFF'.format(channel))
    device.write(':SOUR{}:FUNC:ARB:MODE SRATE'.format(channel))

    print('Sending samples to Output', channel)
    block_size = int(16384/2)  # in uint16 samples. Can send a max 16384 bytes per transfer.
    num_blocks = int(np.floor(len(samples)/block_size))
    if num_blocks > 1:
        for b in range(1, num_blocks):
            device.write_binary_values(':SOURCE{}:TRACE:DATA:DAC16 VOLATILE,CON,'.format(channel), samples[b*block_size:(b+1)*block_size-1], datatype='H')
            print(device.query('*OPC?').rstrip(), '{0:2.2f}'.format(b/num_blocks*100.))
        leftover = len(samples) - num_blocks*block_size
        device.write_binary_values(':SOURCE{}:TRACE:DATA:DAC16 VOLATILE,END,'.format(channel), samples[-leftover:], datatype='H')
        print(device.query('*OPC?').rstrip(), 100.)
    else:
        device.write_binary_values(':SOURCE{}:TRACE:DATA:DAC16 VOLATILE,END,'.format(channel), samples[:block_size], datatype='H')
        print(device.query('*OPC?').rstrip(), 100.)
    # Set the current directory.
    device.write(':SOUR{}:APPL:ARB {},{},{}'.format(channel, fs, high_v-low_v, (high_v+low_v)/2.))
    print(device.query('*OPC?').rstrip())
    device.write(':SYSTem:BEEPer')
    device.close()
    print('Sent {} samples to device'.format(len(samples)))
    return True


def set_vpp(vpp: float, device):
    device.write(':SOUR1:VOLT {}'.format(vpp))


def get_vpp(device):
    vpp = device.query(':SOUR1:VOLT?').rstrip()
    return vpp


def set_load(load: float, device, channel: int):
    if math.isinf(load):
        device.write(':OUTP{}:IMP INF'.format(channel))
    else:
        device.write(':OUTP{}:IMP {}'.format(channel, int(load)))


def get_load(device, channel: int):
    load = device.query(':OUTP1:IMP?').rstrip()
    return load


def crc16(b: bytearray):
    c = crcmod.mkCrcFun(0x11021, 0xEBCC, False, 0x0000)
    return c(b)


def read_raf(inp, dac_values: bool = False):
    if inp is None:
        return None
    elif isinstance(inp, str):
        with open(inp, "rb") as f:
            data = f.read()
    elif isinstance(inp, np.ndarray):
        data = inp
    head_fmt = '<L ? ? ? 25s q l l H H 4x'
    hdr_size = calcsize(head_fmt)
    data_len, b1, b2, fs_mode, filename, fs, high_v, low_v, DataCRC, HeaderCRC = unpack_from(head_fmt, data)
    waveform = unpack_from('<{}H'.format(data_len), data, hdr_size)
    x = np.array(waveform, dtype=np.uint16)
    # header = np.array(unpack_from('<50B', data, 0), dtype=np.uint8)
    # crc_data = crc16(x.tobytes(), 0, 8192*2)
    # crc_head = crc16(header.tobytes(), 0, 50)
    # # Check CRC's match
    # crc_data == DataCRC
    # crc_head == HeaderCRC
    high_v /= 10.**7  # scale to voltage real value
    low_v /= 10.**7   # scale to voltage real value
    filename = filename.decode("utf-8").rstrip()
    if not dac_values:
        x = from_dac_values(x, low_v, high_v)
    if fs_mode:  # sample rate mode
        fs /= 10**6
    else:  # period mode (frequency)
        fs = 10.**6/fs
    print('Read in: {}\n{} samples\n{} Hz\nHigh: {} V, Low: {} V'.format(filename.rstrip(), len(x), fs, high_v, low_v))
    return {'data': x, 'fs': fs, 'high_v': high_v, 'low_v': low_v}


def write_raf(filename: str, samples: np.ndarray, fs_Hz: float, low_v: float, high_v: float):
    # data_u16 = (remap(samples, low_v, high_v, -8191, 8191) + 8191).astype(np.uint16)
    data_u16 = to_dac_values(samples, low_v, high_v)
    crc_data = crc16(data_u16.tobytes(), 0, len(data_u16)*2)
    phead_fmt = '<L ? ? ? 25s q l l H'
    # Period Mode
    # fs_mode = False
    # Fs = int(1./fs_Hz * 10**10)
    # Freq Mode
    fs_mode = True
    fs = int(fs_Hz * 10**6)
    # Limit filename to 25 characters
    if len(filename) > 25:
        filename = filename[:25]
        print('Truncated filename to {}'.format(filename))
    # Extend to 25 characters if needed
    fname = filename + '\x00'*(25-len(filename))
    high_v = int(high_v * 10**7)
    low_v = int(low_v * 10**7)
    header = pack(phead_fmt, len(data_u16), True, False, fs_mode, fname.encode('utf-8'), fs, high_v, low_v, crc_data)
    crc_head = crc16(header, 0, 50)
    header += pack('<Hl', crc_head, 0)
    bin_data = header + data_u16.tobytes()
    f = open(filename, 'wb')
    f.write(bin_data)
    f.close()
    print('{} wrote in with {} samples at {} Hz'.format(filename, len(data_u16), fs/10.**6))


def test():
    try:
        print('main')
        # send_file_to_arb('utils\\write_test.raf')
        # Dummy test data
        # fs = 100e3
        # t = np.arange(fs)/fs
        # fc = fs/8.
        # x = np.cos(2.*np.pi*fc*t)
        # x = np.concatenate((x, np.zeros_like(x)))
        # send_data_to_arb(x, fs=fs, high_v=1., low_v=-1.)
        # send_file_to_arb('arb.raf')
        return False
    except ValueError as ve:
        return str(ve)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Rigol DG1000z series tool')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-r', '--resource', type=int, help='resource index you wish to use')
    group.add_argument('-n', '--name', type=str, help='the resource name to use')
    group.add_argument('-a', '--ip-address', type=str, help='IP address of the resource')
    parser.add_argument('-s', '--scan', action='store_true', help='scan and display available resources')
    parser.add_argument('-f', '--file', type=str, help='path to file to send to arb')
    parser.add_argument('-c', '--channel', type=int, default=1, choices=[1, 2], help='Which channel to use')
    parser.add_argument('-z', '--z-load', type=float, choices=[50, 75, 100, float('inf')], help='Set Load Impedance')
    parser.add_argument('--vpp', type=float, help='Override the Vpp amplitude')
    parser.add_argument('--screenshot', type=str, help='filename to save screenshot to')

    args = parser.parse_args()
    resource = None
    rm = pyvisa.ResourceManager()

    if args.scan:
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()
        for n in range(len(resources)):
            print(n, resources[n])
        sys.exit(0)
    else:
        if args.resource is not None:
            resources = rm.list_resources()
            resource = resources[args.resource]
            print('Using:', resource)
        elif args.name is not None:
            resource = args.name
            print('Using:', resource)
        elif args.ip_address is not None:
            resource = 'TCPIP::{}::INSTR'.format(args.ip_address)
            print('Using:', resource)
        else:
            # sys.exit(test())
            pass

    if args.file is not None:
        if resource is not None:
            send_file_to_arb(args.file, channel=args.channel, device=resource)
        else:
            print('You must specify a resource to use')
            sys.exit(1)

    if args.z_load is not None:
        arb, r = open_device(resource)
        set_load(args.z_load, arb, args.channel)
        print('Load:', get_load(arb, args.channel))
        arb.close()

    # Set Vpp after setting load
    if args.vpp is not None:
        arb, r = open_device(resource)
        set_vpp(args.vpp, arb)
        print('Vpp:', get_vpp(arb))
        arb.close()

    if args.screenshot and resource is not None:
        arb, r = open_device(resource)
        time.sleep(1.0)
        arb.query('*OPC?').rstrip()
        data = arb.query_binary_values(':DISP:DATA?', datatype='c')
        arb.query('*OPC?').rstrip()
        arb.close()
        img = np.array(data)
        img.tofile(args.screenshot)
        print('Screenshot saved to:', args.screenshot)

    sys.exit(0)
