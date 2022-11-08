FROM wert310/gameserver-basechecker:ef3af01

ARG CHROME_VERSION=105.0.5195.52

ENV TZ=Europe/Vienna
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# enable X-forwarding via x11-apps, remove for production
RUN apt-get update \
    && apt-get install -y wget gnupg python3 python3-pip git unzip curl fonts-ipafont-gothic fonts-wqy-zenhei fonts-thai-tlwg fonts-kacst fonts-freefont-ttf libxss1 sqlite3 \
    && wget -O /tmp/chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}-1_amd64.deb \
    && apt install -y /tmp/chrome.deb \
    && rm -rf /var/lib/apt/lists/*

RUN wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CHROME_VERSION}/chromedriver_linux64.zip && cd /usr/bin && unzip /tmp/chromedriver.zip

RUN mkdir -p /checker
WORKDIR /checker

COPY requirements.txt /checker/requirements.txt
RUN pip install -r requirements.txt

COPY checker.py /checker/checker.py
COPY dejavu.ttf /checker/dejavu.ttf

ENV CTF_CHECKERSCRIPT /checker/checker.py
# set this to <yourchallengename>_checker<X>
ENV CTF_SERVICE dewaste_checker2

USER root
ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

USER ctf-checkermaster
ENTRYPOINT ["/tini", "--", "/sbin/docker-entrypoint.sh" ]
