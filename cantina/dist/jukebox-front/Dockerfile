FROM python:3.10.6-alpine
# make sure to use a tag that won't be updated by the image maintainers

RUN addgroup -S cantina && adduser -S cantina -G cantina

RUN mkdir /app
RUN mkdir /data
RUN chown -R cantina:cantina /data
RUN chown -R cantina:cantina /app
WORKDIR /app

# download and install the dependencies first, so these steps can be skipped
# when teams update their service
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY . /app/
RUN chmod a+x /app/run.sh

USER cantina
EXPOSE 10024

CMD /app/run.sh
