FROM wert310/gameserver-basechecker:ef3af01

RUN mkdir -p /checker
WORKDIR /checker

COPY requirements.txt /checker/requirements.txt
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y zip
COPY checker.py firmware_utils.py firmware_generator.py private.pem /checker/
COPY ca.crt commander.crt commander.key /
RUN chmod +x /checker/checker.py
USER ctf-checkermaster
ENV CTF_CHECKERSCRIPT /checker/checker.py
ENV PYTHONUNBUFFERED=1
WORKDIR /checker

# set this to <yourchallengename>_checker<X>
ENV CTF_SERVICE hps_checker2
