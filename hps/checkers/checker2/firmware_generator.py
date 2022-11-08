import subprocess
import tempfile
import uuid

import requests

from firmware_utils import *

extractor = b"""
#!/bin/bash
echo "Extracting firmware..."
unzip data.zip -d target
cd target
find . -type f -exec sha256sum {} \; | sha256sum
"""


def generate_upload_firmware(url, tick, checker_instance):
    result_data = {}
    with tempfile.TemporaryDirectory() as tmpdirname:
        version_hash = uuid.uuid4().hex
        result_data["version_hash"] = version_hash
        version = f"v0.{tick}"
        with open(f"{tmpdirname}/version.py", "w") as f:
            f.write(f"VERSION = \"{version}\"\n")
            f.write(f"HASH = \"{version_hash}\"\n")
        res = subprocess.check_output(["bash", "-c", "find . -type f -exec sha256sum {} \\; | sha256sum"], cwd=tmpdirname)
        inner_hash = res.split(b" ")[0].decode("UTF-8")
        subprocess.check_output(["zip", "-r", f"{tmpdirname}/data.zip", "."], cwd=tmpdirname)
        data = open(f"{tmpdirname}/data.zip", "rb").read()
        packed = pack(extractor, data, inner_hash)
        r=checker_instance.session.post(url, files={"firmware": packed}, timeout=25)
        result_data["response"] = r.status_code
    return result_data
