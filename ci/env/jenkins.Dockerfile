ARG JENKINS_VERSION
ARG JENKINS_SHA
ARG uid
ARG gid
FROM megatron-jenkins-base

ENV MISC_PACKAGES "rsync"
ENV PYTHON_PACKAGES "python-dev python-pip python-virtualenv"

# /var/lib/apt/lists/* is removed by jenkins Dockerfile
USER root
RUN set -ex; \
	mkdir -p /var/lib/apt/lists/partial; \
	apt-get update; \
	apt-get install -y \
		${MISC_PACKAGES} \
		${PYTHON_PACKAGES}; \
	rm -rf /var/lib/apt/lists/*

USER jenkins
