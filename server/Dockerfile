FROM node:20-alpine

WORKDIR /app

# install deps
COPY package*.json ./
RUN npm ci --production=false

# copy source
COPY . .

# build
RUN npm run build

EXPOSE 4000
CMD ["node", "dist/index.js"]
