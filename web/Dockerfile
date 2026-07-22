FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# VITE_API_URL is a BUILD-TIME value baked into the JS bundle by Vite.
# Railway passes service variables as Docker build args, but a build arg is
# only visible to `npm run build` if the stage declares it with ARG. Without
# these two lines the bundle falls back to window.location.origin and the
# frontend calls itself instead of the backend (auth/token requests fail).
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
