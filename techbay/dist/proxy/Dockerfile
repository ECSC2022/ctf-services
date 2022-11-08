FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
RUN adduser caddy -H -D
USER caddy
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
