FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3000 3001

CMD ["sh", "-c", "node result-site/server.js & node social-site/server.js & wait"]
