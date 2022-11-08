import hashlib
import multiprocessing
import os
import subprocess
import sys
import tempfile
import time

import version
from flask import Flask, render_template, send_from_directory, redirect, request
import re
import logging
from importlib import reload
import firmware_utils
import settings
from configuration import ConfigSingleton
from mqtt_handler import MqttClient

app = Flask(__name__)

base = {
    "header_name": "Water flow control",
    "header_location": "Hidden in the mountains",
    "header_contact": "Jimmy"
}

command_log_file = os.environ.get("LOG_PATH", "") + "commands.log"
application_log_file = os.environ.get("LOG_PATH", "") + "application.log"

command_logger = logging.getLogger('instruction_log')
application_logger = logging.getLogger('application_log')


@app.route('/')
def index():  # put application's code here
    reload(version)
    return render_template('index.html', s=ConfigSingleton(), version=version.VERSION, fhash=version.HASH, **base)


@app.route('/logs')
def logs():
    lines = subprocess.check_output(['tail', '-100', application_log_file]).decode('utf-8')
    # All passwords and stuff is wrapped in {} so we can just hide them
    target = []
    for line in lines.splitlines():
        md5 = hashlib.md5(line[23:].encode('utf-8')).hexdigest()
        line = re.sub(r"'operator': '.*',", "'operator': 'HIDDEN FOR PRIVACY'", line)
        target.append(f"{line};{md5}")
    return render_template('logs.html',
                           **base,
                           logs="\n".join(reversed(target)))


@app.route('/command_logs')
def command_logs():
    lines = subprocess.check_output(['tail', '-100', command_log_file]).decode('utf-8')
    # All passwords and stuff is wrapped in {} so we can just hide them
    target = []
    for line in lines.splitlines():
        md5 = hashlib.md5(line[23:].encode('utf-8')).hexdigest()
        line = re.sub(r"'operator': '.*',", "'operator': 'HIDDEN FOR PRIVACY'", line)
        target.append(f"{line};{md5}")
    return render_template('logs.html',
                           **base,
                           logs="\n".join(reversed(target)))


@app.route('/debug')
def debug():
    return render_template('debug.html',
                           **base)


@app.route('/debug/capture')
def debug_capture():
    if not settings.ENABLE_PCAP:
        return "PCAP-Capture is not enabled, please enable in settings first"
    subprocess.call(['sudo', 'tcpdump', '-i', 'eth0', '-G', '60', '-W', '1', '-w', 'pcaps/debug.pcapng'])
    my_hash = sha256sum(f"pcaps/debug.pcapng")

    return redirect('/pcaps/debug.pcapng?hash=' + my_hash)


def sha256sum(filename):
    h = hashlib.sha256()
    b = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        while n := f.readinto(mv):
            h.update(mv[:n])
    return h.hexdigest()


@app.route('/pcaps/<path:path>')
def serve_pcaps(path):
    if not os.path.isfile(f"pcaps/{path}"):
        return "File not found", 404
    my_hash = sha256sum(f"pcaps/{path}")
    if my_hash != request.args.get("hash"):
        application_logger.debug("Hash mismatch for file %s, got %s, expected %s", path, request.args.get("hash"), my_hash)
        return "Hash mismatch", 403
    return send_from_directory('pcaps', path)


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


def firmware_upgrade_process(tmpdirname, data, data_signature, data_hash, return_dict):
    # open the log file, if we need to log something
    f = os.fdopen(os.open(command_log_file, os.O_RDONLY))
    os.chdir(tmpdirname)
    os.chroot(tmpdirname)
    os.chdir("/")

    s_result = subprocess.check_output(["capsh", "--drop=cap_sys_chroot", "--", "-c", "/extractor"], cwd="/", pass_fds=(f.fileno(),))

    inner_hash = s_result.decode("UTF-8").split("\n")[-2].split(" ")[0]
    if inner_hash != data_hash.decode("UTF-8"):
        return_dict["message"] = "Hash mismatch, output was: {}".format(s_result.decode("UTF-8"))
        return
    return_dict["message"] = "Success"


@app.route('/firmware_upgrade', methods=['GET', 'POST'])
def firmware_upgrade():
    if request.method == 'GET':
        return render_template('firmware_upgrade.html', **base)
    if 'firmware' not in request.files:
        return "No file part", 400
    file = request.files['firmware']
    with tempfile.TemporaryDirectory() as tmpdirname:
        file_bytes = file.read()
        extractor, data, data_hash, data_signature = firmware_utils.unpack(file_bytes)
        with open(f"{tmpdirname}/extractor", "wb") as f:
            f.write(extractor)
        with open(f"{tmpdirname}/data.zip", "wb") as f:
            f.write(data)
        subprocess.check_output(['chmod', '+x', f"{tmpdirname}/extractor"])
        firmware_utils.chroot_cp("/bin/bash", f"{tmpdirname}/bin/bash")
        firmware_utils.chroot_cp("/bin/dash", f"{tmpdirname}/bin/dash")
        firmware_utils.chroot_cp("/bin/sh", f"{tmpdirname}/bin/sh")
        firmware_utils.chroot_cp("/bin/rm", f"{tmpdirname}/bin/rm")
        firmware_utils.chroot_cp("/usr/bin/sha256sum", f"{tmpdirname}/usr/bin/sha256sum")
        firmware_utils.chroot_cp("/usr/bin/sort", f"{tmpdirname}/usr/bin/sort")
        firmware_utils.chroot_cp("/usr/bin/find", f"{tmpdirname}/usr/bin/find")
        firmware_utils.chroot_cp("/usr/bin/xargs", f"{tmpdirname}/usr/bin/xargs")
        firmware_utils.chroot_cp("/usr/bin/unzip", f"{tmpdirname}/usr/bin/unzip")
        firmware_utils.chroot_cp("/sbin/capsh", f"{tmpdirname}/sbin/capsh")
        firmware_utils.chroot_cp("/lib/", f"{tmpdirname}/")
        firmware_utils.chroot_cp("/lib64/", f"{tmpdirname}/")
        firmware_utils.chroot_cp("/usr/lib/", f"{tmpdirname}/usr/")
        firmware_utils.chroot_cp("/usr/share/", f"{tmpdirname}/usr/")

        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        proc = multiprocessing.Process(target=firmware_upgrade_process, args=(tmpdirname, data, data_signature, data_hash,return_dict,))
        proc.start()
        proc.join(60)
        if not return_dict["message"] == "Success":
            return return_dict["message"]
        data_c_hash = firmware_utils.hash_sha512(data)
        if not firmware_utils.verify(data_c_hash, int.from_bytes(data_signature, "big")):
            return "Data Signature mismatch"

        subprocess.check_output(["rsync", "-ar", f"{tmpdirname}/target/", "/app"])
        return "SUCCESS"


if __name__ == '__main__':
    command_logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(command_log_file)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    command_logger.addHandler(fh)

    application_logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(application_log_file)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    application_logger.addHandler(fh)

    mqtt_client = MqttClient('hps-mqtt', 10035, 60, ['valve/commands'])
    mqtt_client.daemon = True
    mqtt_client.start()

    app.run(port=10031, host='0.0.0.0', threaded=True)
