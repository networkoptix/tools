FROM ubuntu:16.04


ENV APT_PACKAGES "software-properties-common python-software-properties"

ENV COMMON_PACKAGES "bzip2 unzip xz-utils wget less nano mc screen"
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
ENV BUILD_PACKAGES_GSTREAMER "libgstreamer0.10-0 libgstreamer-plugins-base0.10-0"
ENV BUILD_PACKAGES_XSLT "libxslt1.1"
ENV BUILD_PACKAGES_INSTALLER_TOOLS "zip fakeroot"

# requirements for running x86 cross-compilers
ENV X32_CROSS_PACKAGES "libc6:i386 libncurses5:i386 libstdc++6:i386 lib32z1"

# requirements for running linux-x86 compiler on x86 platform
ENV MULTILIB_PACKAGES "gcc-multilib g++-multilib"

ENV BUILD_PACKAGES_I386_GSTREAMER "libgstreamer0.10-0:i386 libgstreamer-plugins-base0.10-0:i386"
ENV BUILD_PACKAGES_I386_X "libxrender1:i386 libxcomposite1:i386"
ENV BUILD_PACKAGES_I386_OTHER "libglib2.0-dev:i386 libopenal-dev:i386 libglu1-mesa:i386 libldap2-dev:i386 libxss-dev:i386 libxfixes-dev:i386 libxslt1.1:i386 libpng12-0:i386"

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
		${BUILD_PACKAGES_LDAP} \
		${BUILD_PACKAGES_XFIXES} \
		${BUILD_PACKAGES_X11_SCREEN_SAVER_EXTENSION_LIB} \
		${BUILD_PACKAGES_GSTREAMER} \
		${BUILD_PACKAGES_XSLT} \
		${BUILD_PACKAGES_INSTALLER_TOOLS} \
		${FUNTEST_PACKAGES}

RUN set -ex; \
	apt-get install -y \
		${X32_CROSS_PACKAGES} \
		${MULTILIB_PACKAGES} \
		${BUILD_PACKAGES_I386_GSTREAMER} \
		${BUILD_PACKAGES_I386_X} \
		${BUILD_PACKAGES_I386_OTHER}

RUN set -ex; \
	cd /usr/lib/i386-linux-gnu; \
	cp -P libGLU.so.1 libGLU.so; \
	ln -s mesa/libGL.so.1.2.0 libGL.so.1; \
	cp -P libGL.so.1 libGL.so


RUN set -ex; \
	add-apt-repository -y ppa:ubuntu-toolchain-r/test; \
	apt-get update; \
	apt-get install -y gcc-7 g++-7 gcc-7-multilib g++-7-multilib

# Install mercurial from it's own ppa; version available on ubuntu 14 is too old and is incompatible with newer one from jenkins
# todo: may be not nesessary when moved from ubuntu 14 to 16
RUN set -ex; \
	add-apt-repository -y ppa:mercurial-ppa/releases; \
	apt-get update; \
	apt-get install -y mercurial


# Install webadmin build requirements (npm, nodejs and Co)
RUN set -ex; \
	apt-get install -y git npm ruby-compass python-yaml; \
	npm install -g n; \
	n stable

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


# will be mounted to the host
RUN rm /etc/passwd /etc/shadow /etc/group

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
