FROM python:3.8-slim

RUN apt-get update && \
    apt-get install -y \
    libmagickwand-dev curl \
    nginx

COPY requirements.txt .
COPY nginx.conf /etc/nginx/conf.d/default.conf

RUN pip install -r requirements.txt

RUN mkdir /images
RUN mkdir /cache

EXPOSE 5000

COPY app /app

WORKDIR /app

CMD bash entrypoint.sh
