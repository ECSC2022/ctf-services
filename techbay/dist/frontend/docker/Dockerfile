FROM node:16 as builder

WORKDIR /app

COPY ./package.json .
COPY ./yarn.lock .

RUN yarn install

ADD index.html tsconfig.config.json tsconfig.json vite.config.ts env.d.ts ./
ADD src/ ./src/
ADD public/ ./public/

RUN yarn run build

FROM alpine:3.16.2

RUN apk add thttpd

RUN adduser -D static
WORKDIR /home/static

COPY --from=builder /app/dist/ .

RUN chown -R static:static /home/static

USER static

CMD ["thttpd", "-D", "-h", "0.0.0.0", "-p", "8080", "-d", "/home/static", "-u", "static", "-l", "-", "-M", "60"]

EXPOSE 8080
