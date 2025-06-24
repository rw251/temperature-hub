FROM node:18-alpine

RUN apk add --no-cache git python3 py3-pip

COPY web /app

WORKDIR /app

EXPOSE 8000

CMD ["python3", "-m", "http.server", "8000", "--directory", "/app"]

