from vgm_parser import Vgm
import time
import struct
from pathlib import Path
import gzip
import argtyper

import logging


def main(path : Path, verify_only : bool =False):
    data = ''
    print(path)
    if path.suffix == '.vgz':
        with gzip.open(path, 'rb') as f:
            data = f.read()
    else:
        with open(path, 'rb') as f:
            data = f.read()
    vgm = Vgm.from_bytes(data)
    #print(bytes(vgm.gd3.track).decode('ascii'))
    #print(bytes(vgm.gd3.author).decode('ascii'))
    #print(bytes(vgm.gd3.notes).decode('ascii'))
    
    clock = 1 / 44100
    vgm.data
    
    start = time.time()
    index = 0
    wait = 0
    regs = [0] * 0x20
    msg_count = 0 
    
    bus = None


    try:
        if not verify_only:
            import can
            bus = can.Bus(
            interface="socketcan",
            channel="vcan0",
            receive_own_messages=False,
            fd=True,
            )
            
        dirty = 0
        while True:
            wait = 0
            cmd = vgm.data[index]
            index += 1
            if cmd == 0xB4:
                reg = vgm.data[index]
                val = vgm.data[index+1]
                index += 2
                if reg > 0x20:
                    raise IndexError(f"Index '{reg}' out of range")
                #if regs[reg] != val:
                regs[reg] = val
                dirty = dirty | (1 << reg)
                #else:
                #     print(f"Re-writing: {reg:0>2x} <- {val:b}")
            elif cmd == 0x62:
                wait = 735
            elif cmd == 0x63:
                wait = 882
            elif cmd == 0x61:
                wait = int.from_bytes(vgm.data[index:index+2], 'little')
                index += 2
            elif (cmd & 0xf0) == 0x70:
                wait = cmd & 0xf
            elif cmd == 0x66:
                break
            else:
                raise ValueError(f'Unknow cmd 0x{cmd:x}')
        
        
            if dirty and wait:
                #print(' '.join(f'{x:>3}' for x in regs))
                if not verify_only:
                    msg = can.Message(arbitration_id=0x7, data = list(dirty.to_bytes(3, 'little')) + regs, is_fd=True, is_extended_id=False)
                    bus.send(msg)
                msg_count += 1
                dirty = 0
            
            if wait != 0 and not verify_only:
                time.sleep((wait-1) * clock)
                pass
    except ValueError as e:
        logging.error(f"Error in {path} ({e})")
        return 1
    except IndexError as e:
        logging.error(f"Error in {path} ({e})")
        return 1
    finally:
        if bus:
            bus.close()
    end = time.time()
    print("Time:", end - start)
    print("Msg#:", msg_count)

import sys

if __name__ == "__main__":
    at = argtyper.ArgTyper(main)
    at()
