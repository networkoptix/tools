FROM ubuntu:14.04


ENV COMMON_PACKAGES "bzip2 unzip xz-utils wget mercurial"
ENV JAVA_REQUIREMENTS_PACKAGES "ca-certificates-java libasound2"
ENV PYTHON_PACKAGES "python-dev python-pip python-virtualenv"
ENV JUNK_SHOP_PACKAGES "libpq-dev gdb"
ENV CMAKE_BUILD_PACKAGES "ninja-build"
ENV FUNTEST_PACKAGES "python-demjson python-opencv"


RUN set -ex; \
	apt-get update; \
	apt-get install -y \
		${COMMON_PACKAGES} \
		${JAVA_REQUIREMENTS_PACKAGES} \
		${PYTHON_PACKAGES} \
		${JUNK_SHOP_PACKAGES} \
		${CMAKE_BUILD_PACKAGES} \
		${FUNTEST_PACKAGES}


# Install java 8
# no jdk-8 in ubuntu 14.04, using Azul debian for it:
ARG JDK_DEB=zulu8.21.0.1-jdk8.0.131-linux_amd64.deb
RUN set -ex; \
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
