##########################################################################################################
# Builder
##########################################################################################################
FROM node:16 AS builder

RUN apt-get update  \
 && apt-get install -y \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package.json
COPY package-lock.json package-lock.json

RUN npm ci

COPY . .

RUN npm run asbuild:release
