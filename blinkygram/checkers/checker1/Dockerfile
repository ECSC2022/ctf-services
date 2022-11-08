FROM wert310/gameserver-basechecker:ef3af01

RUN mkdir -p /checker
WORKDIR /checker

COPY requirements.txt /checker/requirements.txt
RUN pip install -r requirements.txt

COPY *.py /checker/
USER ctf-checkermaster
ENV CTF_CHECKERSCRIPT /checker/checker.py

ENV CTF_SERVICE blinkygram_checker1
