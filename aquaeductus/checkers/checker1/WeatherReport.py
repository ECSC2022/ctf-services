#!/usr/bin/env python3
from numpy.random import Generator, default_rng
import struct
import sys


def generate_weather_report(rng: Generator, num_nodes: int, has_extra_params=False):
    output = b''

    rands1 = rng.random(num_nodes)
    for i in range(0, num_nodes):
        output += struct.pack("<d", rands1[i])

    rands2 = None
    if has_extra_params:
        output += b"\n"
        rands2 = rng.random(num_nodes)
        for i in range(0, num_nodes):
            output += struct.pack("<d", rands2[i])

    output += b"\n"

    return output, rands1, rands2


if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.stderr.write('Usage: ./WeatherReport.py report num_nodes extra_param append?\n')
        sys.exit(1)

    file = sys.argv[1]
    num = int(sys.argv[2])
    extra = sys.argv[3] == "1" or sys.argv[3] == "true"
    append = (sys.argv[4] if len(sys.argv) > 4 else "").encode()

    output, _, _ = generate_weather_report(default_rng(), num, extra)
    output = output + append

    with open(file, 'wb') as f:
        f.write(output)
