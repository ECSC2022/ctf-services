#!/usr/bin/env python3
import signal
import subprocess
import sqlite3
import os
from pathlib import Path
from threading import Event


def do_cleanup(data_dir: Path):
    try:
        # Cleanup upload folder
        subprocess.call([
            "/usr/bin/find",
            str(data_dir / "uploads"),
            "-mmin", "+30",
            "-delete"
        ])
    except Exception as ex:
        print(f"Got {ex}, continuing")

    ## Cleanup sqlite database
    #try:
    #    con = sqlite3.connect(data_dir / "user.db")
    #    con.execute('delete from files where created <= datetime("now", "-30 minute")')
    #    con.close()
    #except Exception as ex:
    #    print(f"Got {ex}, continuing")


if __name__ == '__main__':
    stop = Event()

    def quit(_, __):
        stop.set()
    for sig in('TERM', 'HUP', 'INT'):
        signal.signal(getattr(signal, 'SIG'+sig), quit)

    data_dir = Path(os.environ.get("DATA_DIR", "/data"))

    while not stop.is_set():
        do_cleanup(data_dir)
        stop.wait(120)
