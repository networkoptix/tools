FROM ubuntu:14.04


ENV COMMON_PACKAGES "bzip2 unzip xz-utils wget mercurial"
ENV JAVA_REQUIREMENTS_PACKAGES "ca-certificates-java libasound2"
ENV PYTHON_PACKAGES "python-dev python-pip python-virtualenv"
ENV JUNK_SHOP_PACKAGES "libpq-dev gdb"
ENV CMAKE_BUILD_PACKAGES "rsync ninja-build"
ENV BUILD_PACKAGES_ZLIB "zlib1g-dev"
ENV BUILD_PACKAGES_OPENAL "libopenal-dev"
ENV BUILD_PACKAGES_MESA "mesa-common-dev libgl1-mesa-dev libglu1-mesa-dev"
ENV BUILD_PACKAGES_LDAP "libldap2-dev"
ENV BUILD_PACKAGES_XFIXES "libxfixes-dev"
ENV BUILD_PACKAGES_X11_SCREEN_SAVER_EXTENSION_LIB "libxss-dev"
ENV BUILD_PACKAGES_MORE "libgstreamer0.10 libxslt1.1"
ENV BUILD_PACKAGES "${BUILD_PACKAGES_ZLIB} ${BUILD_PACKAGES_OPENAL} ${BUILD_PACKAGES_MESA} ${BUILD_PACKAGES_LDAP} ${BUILD_PACKAGES_XFIXES} ${BUILD_PACKAGES_X11_SCREEN_SAVER_EXTENSION_LIB} ${BUILD_PACKAGES_MORE}"
ENV FUNTEST_PACKAGES "python-demjson python-opencv"


RUN set -ex; \
	apt-get update; \
	apt-get install -y \
		${COMMON_PACKAGES} \
		${JAVA_REQUIREMENTS_PACKAGES} \
		${PYTHON_PACKAGES} \
		${JUNK_SHOP_PACKAGES} \
		${CMAKE_BUILD_PACKAGES} \
		${BUILD_PACKAGES} \
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
