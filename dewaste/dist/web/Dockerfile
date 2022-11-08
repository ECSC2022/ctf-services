FROM composer:2.4.1 AS builder

RUN adduser --disabled-password --gecos '' builder
USER builder
WORKDIR /home/builder

COPY composer.json composer.lock ./
RUN composer install --no-dev

COPY src/App ./App
RUN composer dump-autoload -o


FROM composer:2.4.1 AS tester

RUN adduser --disabled-password --gecos '' builder
USER builder
WORKDIR /home/builder

COPY composer.json composer.lock ./
RUN composer install

COPY src ./src
RUN composer dump-autoload -o

COPY phpcs.xml ./
RUN ./vendor/bin/phpcs
COPY phpstan.neon ./
RUN ./vendor/bin/phpstan 2> /dev/null


FROM php:8.1.9-apache
RUN apt-get update

# Install Postgres PDO
RUN apt-get install -y libpq-dev \
    && docker-php-ext-configure pgsql -with-pgsql=/usr/local/pgsql \
    && docker-php-ext-install pdo pdo_pgsql pgsql

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

RUN sed -i 's#AllowOverride [Nn]one#AllowOverride All#' /etc/apache2/apache2.conf
RUN a2enmod rewrite
RUN echo 'error_reporting=E_ERROR|E_WARNING' >> /usr/local/etc/php/conf.d/logging.ini
RUN echo 'display_errors=off' >> /usr/local/etc/php/conf.d/logging.ini
RUN echo 'log_errors=on' >> /usr/local/etc/php/conf.d/logging.ini

RUN echo 'Listen 8080' > /etc/apache2/ports.conf
RUN sed -i 's#VirtualHost *:80#VirtualHost *:8080#' /etc/apache2/sites-enabled/000-default.conf
RUN chown -R www-data /var/log/apache2 /var/run/apache2

RUN mkdir -p /var/lib/recycling_plant
VOLUME /var/lib/recycling_plant
RUN chown www-data:www-data /var/lib/recycling_plant

VOLUME /var/run/apache2

USER "www-data"

COPY docker/app-cron.sh docker/entrypoint.sh /

COPY --from=builder /home/builder/vendor /var/www/html/vendor
COPY ./src /var/www/html

CMD ["/entrypoint.sh"]