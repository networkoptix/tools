FROM ubuntu:14.04


ENV APT_PACKAGES "software-properties-common python-software-properties"

# requirements for running x86 cross-compilers
ENV X32_PACKAGES "libc6:i386 libncurses5:i386 libstdc++6:i386 lib32z1"

# requirements for running linux-x86 compiler on x86 platform
ENV MULTILIB_PACKAGES "gcc-multilib g++-multilib"

ENV COMMON_PACKAGES "bzip2 unzip xz-utils wget"
ENV JAVA_REQUIREMENTS_PACKAGES "ca-certificates-java libasound2"
ENV PYTHON_PACKAGES "python-dev python-pip python-virtualenv"
ENV JUNK_SHOP_PACKAGES "libpq-dev gdb"
ENV CMAKE_BUILD_PACKAGES "rsync ninja-build"

ENV BUILD_PACKAGES_ZLIB "zlib1g-dev zlib1g-dev:i386"
ENV BUILD_PACKAGES_OPENAL "libopenal-dev libopenal-dev:i386"
ENV BUILD_PACKAGES_MESA "mesa-common-dev libgl1-mesa-dev libglu1-mesa-dev"
ENV BUILD_PACKAGES_MESA_I386 "libgl1-mesa-glx:i386"
ENV BUILD_PACKAGES_LDAP "libldap2-dev libldap2-dev:i386"
ENV BUILD_PACKAGES_XFIXES "libxfixes-dev libxfixes-dev:i386"
ENV BUILD_PACKAGES_X11_SCREEN_SAVER_EXTENSION_LIB "libxss-dev libxss-dev:i386"
ENV BUILD_PACKAGES_GSTREAMER "libgstreamer0.10 libgstreamer0.10-0:i386 libgstreamer-plugins-base0.10-0:i386"
ENV BUILD_PACKAGES_XSLT "libxslt1.1 libxslt1.1:i386"
ENV BUILD_PACKAGES_X_I386 "libxrender1:i386 libxcomposite1:i386"
ENV BUILD_PACKAGES_INSTALLER_TOOLS "zip"

ENV FUNTEST_PACKAGES "python-demjson python-opencv"


RUN set -ex; \
	dpkg --add-architecture i386; \
	apt-get update; \
	apt-get install -y \
		${APT_PACKAGES} \
		${COMMON_PACKAGES} \
		${JAVA_REQUIREMENTS_PACKAGES} \
		${PYTHON_PACKAGES} \
		${JUNK_SHOP_PACKAGES} \
		${CMAKE_BUILD_PACKAGES} \
		${BUILD_PACKAGES_ZLIB} \
		${BUILD_PACKAGES_OPENAL} \
		${BUILD_PACKAGES_MESA} \
		${BUILD_PACKAGES_MESA_I386} \
		${BUILD_PACKAGES_LDAP} \
		${BUILD_PACKAGES_XFIXES} \
		${BUILD_PACKAGES_X11_SCREEN_SAVER_EXTENSION_LIB} \
		${BUILD_PACKAGES_GSTREAMER} \
		${BUILD_PACKAGES_XSLT} \
		${BUILD_PACKAGES_INSTALLER_TOOLS} \
		${FUNTEST_PACKAGES}

RUN set -ex; \
	apt-get install -y \
		${X32_PACKAGES} \
		${MULTILIB_PACKAGES} \
		${BUILD_PACKAGES_X_I386}


# Install mercurial from it's own ppa; version available on ubuntu 14 is too old and is incompatible with newer one from jenkins
RUN set -ex; \
	add-apt-repository -y ppa:mercurial-ppa/releases; \
	apt-get update; \
	apt-get install -y mercurial


# Install java 8
# no jdk-8 in ubuntu 14.04, using Azul debian for it:
ARG JDK_DEB=zulu8.21.0.1-jdk8.0.131-linux_amd64.deb
RUN set -ex; \
	cd /tmp; \
	wget --no-verbose http://cdn.azul.com/zulu/bin/${JDK_DEB}; \
	dpkg -i ${JDK_DEB} || apt-get install --fix-broken --yes; \
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
