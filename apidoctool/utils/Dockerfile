# Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

# ---------------------------------------------------------------------------
# Stage 1 – Compiles all Java sources, producing apidoctool.jar.
# ---------------------------------------------------------------------------
FROM --platform=linux/amd64 gradle:8.7-jdk8 AS apidoctool-builder

WORKDIR /build

COPY build.gradle /build/build.gradle

COPY src /build/src
COPY artifacts /build/artifacts

ENV GRADLE_OPTS="-Dorg.gradle.daemon=false"
RUN gradle jar

# ---------------------------------------------------------------------------
# Stage 2 – Python/tools image extended with the built artifacts.
# ---------------------------------------------------------------------------
FROM --platform=linux/amd64 python:3.12-slim-bookworm

ARG CONAN_SOURCE_URL=https://artifactory.nxvms.dev/artifactory/artifacts
ARG SWAGGER_VERSION=3.0.21
ARG JD_VERSION=1.9.1
ARG DELTA_VERSION=0.18.2

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    git \
    jq \
    openjdk-17-jre-headless \
    && python3 -m pip install --no-cache-dir  \
      conan==1.64.1 \
      pytest==9.0.3 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fSL -o /usr/local/bin/jd "https://github.com/josephburnett/jd/releases/download/v${JD_VERSION}/jd-amd64-linux" && \
    chmod +x /usr/local/bin/jd && \
    curl -fSL -o delta.tgz "https://github.com/dandavison/delta/releases/download/${DELTA_VERSION}/delta-${DELTA_VERSION}-x86_64-unknown-linux-musl.tar.gz" && \
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
COPY utils/apidoc_diff.py /utils/run_apidoctool.py /app/
COPY utils/apidoc_diff /app/apidoc_diff

# Copy artifacts from builder stages.
COPY --from=apidoctool-builder /build/build/libs/apidoctool.jar /app/apidoctool.jar

RUN curl -fSL -o /app/cli.jar \
    "${CONAN_SOURCE_URL}/conan/sources/swagger-codegen/${SWAGGER_VERSION}/swagger-codegen-cli-${SWAGGER_VERSION}.jar"

RUN ln -s /app/apidoc_diff.py /usr/local/bin/apidoc_diff

ENV PYTHONUNBUFFERED=1 \
    JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64 \
    APIDOCTOOL_JAR=/app/apidoctool.jar \
    SWAGGER_CODEGEN_JAR=/app/cli.jar

ENV PATH="$JAVA_HOME/bin:$PATH"

USER user

WORKDIR /workdir

ENTRYPOINT ["bash", "-c"]
