# Stage 1: build Tailwind CSS
FROM node:22-alpine AS css
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY assets ./assets
COPY lumen/templates ./lumen/templates
COPY public ./public
RUN npm run build:css

# Stage 2: Flask app served by gunicorn
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOCAL_STORAGE_DIR=/data
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY . .
COPY --from=css /app/public/static/css/app.css ./public/static/css/app.css
RUN useradd --create-home lumen && mkdir -p /data && chown lumen /data
USER lumen
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:app"]
