# Stage 1: Build the React app
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# VITE_API_URL defaults to /api so it works behind any ingress/proxy
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

RUN npx vite build

# Stage 2: Serve the built assets with nginx
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
