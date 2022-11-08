import gzip
import logging
import struct
import time
from pathlib import Path

from .parser import Vgm


class VGM:
    def __init__(self):
        self.data = None
        self.vgm = None
        self.clock = 1 / 44100

    def parse_file(self, path):
        if path.suffix == ".vgz":
            with gzip.open(path, "rb") as f:
                data = f.read()
        else:
            with open(path, "rb") as f:
                data = f.read()
        self.data = data
        self.vgm = Vgm.from_bytes(data)

    def parse_memory(self, data, suffix):
        if suffix == ".vgz":
            data = gzip.decompress(data)
        self.data = data
        self.vgm = Vgm.from_bytes(data)

    def file_info(self):
        if not self.vgm:
            return
        return dict(
                track=self.vgm.gd3.track,
                track_jp=self.vgm.gd3.track_jp,
                game=self.vgm.gd3.game,
                game_jp=self.vgm.gd3.game_jp,
                system=self.vgm.gd3.system,
                system_jp=self.vgm.gd3.system_jp,
                author=self.vgm.gd3.author,
                author_jp=self.vgm.gd3.author_jp,
                release_date=self.vgm.gd3.release_date,
                converted_by=self.vgm.gd3.converted_by,
                notes=self.vgm.gd3.notes,
                )

    def str_to_bytes(self, value):
        out = b''
        for x in value:
            val = ord(x)
            out += val.to_bytes(2, 'little')
        out += b'\x00\x00'
        return out

    def dump_gd3_tag(self, data):
        out = b""
        for x in ['track', 'game', 'system', 'author']:
            out+= self.str_to_bytes( data[x]  )
            out+= self.str_to_bytes( data[x +'_jp']  )
        
        out+= self.str_to_bytes( data['release_date']  )
        out+= self.str_to_bytes( data['converted_by']  )
        out+= self.str_to_bytes( data['notes']  )
        return out
        

    def _array_to_str(self, arr):
        output = ''
        for x in arr:
            output += chr(x)
        return output.strip('\x00')

    def parsed_info(self):
        info = self.file_info() 
        return {x : self._array_to_str(y) for x,y in info.items()}


    def verify(self):
        if not self.vgm:
            return False

        start = time.time()
        dirty = 0
        index = 0
        wait = 0
        regs = [0] * 0x20
        pass

        try:
            dirty = 0
            while True:
                wait = 0
                cmd = self.vgm.data[index]
                index += 1
                if cmd == 0xB4:
                    reg = self.vgm.data[index]
                    val = self.vgm.data[index + 1]
                    index += 2
                    if reg > 0x20:
                        raise IndexError(f"Index '{reg}' out of range")
                    # if regs[reg] != val:
                    regs[reg] = val
                    dirty = dirty | (1 << reg)
                    # else:
                    #     print(f"Re-writing: {reg:0>2x} <- {val:b}")
                elif cmd == 0x62:
                    wait = 735
                elif cmd == 0x63:
                    wait = 882
                elif cmd == 0x61:
                    wait = int.from_bytes(self.vgm.data[index : index + 2], "little")
                    index += 2
                elif (cmd & 0xF0) == 0x70:
                    wait = cmd & 0xF
                elif cmd == 0x66:
                    break
                else:
                    raise ValueError(f"Unknow cmd 0x{cmd:x}")

        except ValueError as e:
            logging.error(f"Error in {path} ({e})")
            return False
        except IndexError as e:
            logging.error(f"Error in {path} ({e})")
            return False

        end = time.time()
        print("Time:", end - start)

        return True

    def play(self, file):
        pass


def main(path: Path, verify_only: bool = False):
    data = ""
    print(path)
    if path.suffix == ".vgz":
        with gzip.open(path, "rb") as f:
            data = f.read()
    else:
        with open(path, "rb") as f:
            data = f.read()
    vgm = Vgm.from_bytes(data)
    # print(bytes(vgm.gd3.track).decode('ascii'))
    # print(bytes(vgm.gd3.author).decode('ascii'))
    # print(bytes(vgm.gd3.notes).decode('ascii'))

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
                val = vgm.data[index + 1]
                index += 2
                if reg > 0x20:
                    raise IndexError(f"Index '{reg}' out of range")
                # if regs[reg] != val:
                regs[reg] = val
                dirty = dirty | (1 << reg)
                # else:
                #     print(f"Re-writing: {reg:0>2x} <- {val:b}")
            elif cmd == 0x62:
                wait = 735
            elif cmd == 0x63:
                wait = 882
            elif cmd == 0x61:
                wait = int.from_bytes(vgm.data[index : index + 2], "little")
                index += 2
            elif (cmd & 0xF0) == 0x70:
                wait = cmd & 0xF
            elif cmd == 0x66:
                break
            else:
                raise ValueError(f"Unknow cmd 0x{cmd:x}")

            if dirty and wait:
                # print(' '.join(f'{x:>3}' for x in regs))
                if not verify_only:
                    msg = can.Message(
                        arbitration_id=0x7,
                        data=list(dirty.to_bytes(3, "little")) + regs,
                        is_fd=True,
                        is_extended_id=False,
                    )
                    bus.send(msg)
                msg_count += 1
                dirty = 0

            if wait != 0 and not verify_only:
                time.sleep((wait - 1) * clock)
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
