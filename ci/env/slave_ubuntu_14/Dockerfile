FROM ubuntu:14.04


RUN set -ex; \
	apt-get update; \
	apt-get install -y \
		bzip2 \
		unzip \
		xz-utils \
		ca-certificates-java \
		wget \
		mercurial


# Install java 8
# no jdk-8 in ubuntu 14.04, using Azul debian for it:
ARG JDK_DEB=zulu8.21.0.1-jdk8.0.131-linux_amd64.deb
RUN set -ex; \
	apt-get install -y libasound2; \
	cd /tmp; \
	wget --no-verbose http://cdn.azul.com/zulu/bin/${JDK_DEB}; \
	dpkg -i ${JDK_DEB}; \
	rm ${JDK_DEB}


# Install ssh server
ENV TERM xterm
RUN set -ex; \
	apt-get install -y openssh-server; \
	mkdir /var/run/sshd


# Create jenkins user
ENV HOME=/jenkins
ARG uid
ARG gid
RUN set -ex; \
	addgroup --gid ${gid} jenkins; \
	useradd --uid ${uid} --gid ${gid} --home-dir "$HOME" --create-home --shell /bin/bash jenkins


EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
