FROM python:3.10

RUN apt-get update && apt-get install -y zip sudo

RUN useradd server && useradd userbackup
RUN echo 'server ALL=(userbackup:userbackup) NOPASSWD: ALL' >> /etc/sudoers

WORKDIR /app

RUN mkdir /app/storage && chmod 777 /app/storage

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY *.py ./

USER server

ENTRYPOINT ["./main.py"]
