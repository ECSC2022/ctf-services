FROM node:16 as builder

WORKDIR /app

COPY ./package.json .
COPY ./yarn.lock .

RUN yarn install

ADD tsconfig.json private.ke[y] ./
ADD src/ ./src/

RUN yarn run build

FROM node:16 as runner

WORKDIR /app

COPY --from=builder /app/node_modules/ ./node_modules/
COPY --from=builder /app/build/ /app/private.ke[y] ./

RUN chown -R node:node /app

USER node

ENTRYPOINT ["node", "./index.js"]

EXPOSE 8080
