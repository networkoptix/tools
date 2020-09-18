FROM python:3.8-alpine

COPY requirements.txt .
RUN apk add --no-cache tini && \
    pip3 install -r requirements.txt 

ARG APP_UID=1000
ARG APP_GID=1000

WORKDIR /workdir
RUN addgroup --gid $APP_GID workflow-robocat && \
    adduser --uid $APP_UID --disabled-password --ingroup workflow-robocat workflow-robocat && \
    install -d /workdir/ -o $APP_UID -g $APP_GID

USER workflow-robocat

COPY ./ /workdir/

ENTRYPOINT ["/sbin/tini", "--", "/workdir/robocat.app"]
