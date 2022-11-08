# start by pulling the python image
FROM python:3.8-alpine

# update and install sqlite3 and building toolchain for cryptography
RUN apk update && apk add --upgrade sqlite build-base libffi-dev

# switch working directory
WORKDIR /app

# copy every content from the local file to the image
COPY . /app

# install the dependencies and packages in the requirements file
RUN pip install -r requirements.txt

# create a new DB
RUN rm -f report.db
RUN sqlite3 report.db < schema.sql

ENTRYPOINT [ "python" ]
CMD [ "report.py" ]