FROM ubuntu:20.04 as builder
RUN apt-get update && apt-get install --yes --no-install-recommends \
    cmake \
    gfortran \
    make

RUN mkdir /src /build

COPY src /src
RUN cd /src/deps/fortran-unix && \
    make clean linux
RUN cd /build && \
    cmake /src -DFORTRAN_UNIX_DIR=/src/deps/fortran-unix && \
    make

FROM ubuntu:20.04
COPY run.sh /run.sh
COPY cleanup-cron /etc/cron.d/cleanup-cron
RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
        cron \
        libgfortran5 \
        socat && \
    useradd service && \
    chmod u+s /usr/sbin/cron && \
    crontab -u service /etc/cron.d/cleanup-cron && \
    mkdir -p /data && \
    chown service:service /data

USER service
COPY --from=builder /build/winds_of_the_past /service
CMD /run.sh
