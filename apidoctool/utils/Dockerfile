# Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

FROM --platform=linux/amd64 python:3.11-slim-bullseye

ARG JD_VERSION=1.9.1
ARG DELTA_VERSION=0.18.2

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    git \
    python3 \
    && python3 -m pip install --no-cache-dir conan==1.64.1 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -L -o /usr/local/bin/jd "https://github.com/josephburnett/jd/releases/download/v${JD_VERSION}/jd-amd64-linux" && \
    chmod +x /usr/local/bin/jd && \
    curl -L -o delta.tgz "https://github.com/dandavison/delta/releases/download/${DELTA_VERSION}/delta-${DELTA_VERSION}-x86_64-unknown-linux-musl.tar.gz" && \
    tar xf delta.tgz && \
    mv delta*/delta /usr/local/bin && \
    rm -rf /tmp/delta* && \
    [ -x /usr/local/bin/jd ] && \
    [ -x /usr/local/bin/delta ]

ARG APP_UID=1000
ARG APP_GID=1000

RUN addgroup --gid $APP_GID user && \
    adduser --uid $APP_UID --disabled-password --ingroup user user && \
    install -d /workdir/ -o $APP_UID -g $APP_GID && \
    mkdir -p /app/apidoc_diff && chown user:user /workdir 

WORKDIR /app
COPY ./apidoc_diff.py ./run_apidoctool.py /app/
COPY ./apidoc_diff/* /app/apidoc_diff

RUN ln -s /app/apidoc_diff.py /usr/local/bin/apidoc_diff

USER user

WORKDIR /workdir

ENTRYPOINT ["bash", "-c"]

