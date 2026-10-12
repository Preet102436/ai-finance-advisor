# Dev-mode container (runs the same Vite dev server you'd run locally) -
# simplest way to hand someone a working copy without them installing Node.
# Not a production build.
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
