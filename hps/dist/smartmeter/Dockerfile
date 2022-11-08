FROM python:3.10-slim-buster

COPY requirements.txt /requirements.txt

RUN pip install -r /requirements.txt

COPY . /app

WORKDIR /app

ENV PYTHONUNBUFFERED=1
RUN mkdir /data && chown -R 1000:1000 /data
RUN useradd -ms /bin/bash user
USER user

CMD ["bash", "-c", "python3 manage.py migrate && python3 -u manage.py runserver 0.0.0.0:10030 --noreload"]
