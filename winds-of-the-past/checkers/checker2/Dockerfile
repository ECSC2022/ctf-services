FROM wert310/gameserver-basechecker:ef3af01

RUN apt-get update && apt-get install --yes --no-install-recommends \
    gfortran

RUN mkdir -p /checker
WORKDIR /checker

COPY requirements.txt /checker/requirements.txt
RUN pip install -r requirements.txt

COPY checksum.f /checker/checksum.f
RUN gfortran /checker/checksum.f -fdec-structure -o /checker/checksum

COPY checker.py /checker/checker.py

USER ctf-checkermaster
ENV CTF_CHECKERSCRIPT /checker/checker.py

# set this to <yourchallengename>_checker<X>
ENV CTF_SERVICE winds-of-the-past_checker2
