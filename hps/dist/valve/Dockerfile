FROM python:3.10-slim-buster

COPY requirements.txt /requirements.txt

RUN pip install -r /requirements.txt

RUN apt-get update && apt-get install -y zip libcap2-bin rsync

COPY . /app

WORKDIR /app
ENV PYTHONUNBUFFERED=1

CMD ["bash", "entry.sh"]