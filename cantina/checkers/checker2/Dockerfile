FROM wert310/gameserver-basechecker:ef3af01

RUN mkdir -p /checker
WORKDIR /checker

# Add requirements
COPY checker2/requirements.txt /checker/requirements.txt
RUN pip install -r requirements.txt

# Add common cantina files/modules
COPY checker2/music /checker/music
COPY common/cantina/cantina /checker/cantina
COPY common/cantinautils /checker/cantinautils
COPY checker2/vgm /checker/vgm
COPY common/message-ids.yaml /conf/message-ids.yaml

# Add checker
COPY checker2/checker.py /checker/checker.py
USER ctf-checkermaster
ENV CTF_CHECKERSCRIPT /checker/checker.py

# set this to <yourchallengename>_checker<X>
ENV CTF_SERVICE cantina_checker2
