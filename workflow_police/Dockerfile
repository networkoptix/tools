FROM python:3.8-alpine

COPY requirements.txt .
RUN apk add --no-cache tini gcc musl-dev libffi-dev openssl-dev git openssh-client && \
    pip3 install -r requirements.txt && \
    apk del gcc musl-dev libffi-dev openssl-dev

ARG APP_UID=1000
ARG APP_GID=1000

WORKDIR /workdir
RUN addgroup --gid $APP_GID workflow-police && \
    adduser --uid $APP_UID --disabled-password --ingroup workflow-police workflow-police && \
    install -d /workdir/ -o $APP_UID -g $APP_GID

USER workflow-police

COPY ./ /workdir/

ENTRYPOINT ["/sbin/tini", "--", "/workdir/workflow_police.py"]
