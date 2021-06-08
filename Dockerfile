FROM python:3.6-alpine


COPY requirements.txt /
COPY dev-requirements.txt /

RUN set -eux \
    && apk add --no-cache --virtual .build-deps build-base \
        libressl-dev libffi-dev gcc musl-dev python3-dev \
    && pip install --upgrade pip setuptools wheel \
    && pip install -r /requirements.txt \
    && pip install -r dev-requirements.txt \
    && rm -rf /root/.cache/pip

WORKDIR /motley_cue

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FEUDAL_ADAPTER_CONFIG /etc/motley_cue/feudal_adapter.conf

COPY ./etc /etc/motley_cue
COPY ./tests/configs /tests/configs
COPY . /motley_cue
