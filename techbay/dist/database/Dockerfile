FROM postgres:14.5

COPY schema.sql /docker-entrypoint-initdb.d/schema.sql

USER postgres
EXPOSE 5432