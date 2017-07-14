#!/bin/bash -xe

function die() {
	echo "$@" 1>&2
	exit 1
}

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
	software-properties-common  # provides add-apt-repository

add-apt-repository ppa:ubuntu-toolchain-r/test  # using newest gcc from here

JUNK_SHOP_REQUIREMENTS="libpq-dev python-dev gdb"
MAVEN_BUILD_REQUIREMENTS="maven"
CMAKE_BUILD_REQUIREMENTS="ninja-build"

apt-get install -y --no-install-recommends \
    protobuf-compiler \
    build-essential \
    unzip zip \
    libz-dev \
    libasound2 \
    libxrender-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    libxrandr-dev \
    libxinerama-dev \
    libxcursor-dev \
    libopenal-dev \
    mesa-common-dev \
    freeglut3 \
    freeglut3-dev \
    libglu1-mesa-dev \
    chrpath \
    libxss-dev \
    libasound2 \
    libxrender-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    libgstreamer0.10-dev \
    libgstreamer-plugins-base0.10-0 \
    libncurses5-dev \
    libxslt1-dev \
    libsqlite3-dev \
    libstdc++6-4.7-dev \
    python-virtualenv \
    libldap2-dev \
    python-software-properties \
    g++-4.8 \
    rsync \
    mercurial \
    fakeroot \
    python-demjson \
    python-opencv \
    $JUNK_SHOP_REQUIREMENTS \
    $MAVEN_BUILD_REQUIREMENTS \
    $CMAKE_BUILD_REQUIREMENTS

# install jre 1.8 required for jenkins with jre 1.8
cd /tmp
wget --no-verbose --no-cookies --no-check-certificate --header \
	 "Cookie: gpw_e24=http%3A%2F%2Fwww.oracle.com%2F; oraclelicense=accept-securebackup-cookie" \
	 http://download.oracle.com/otn-pub/java/jdk/8u131-b11/d54c1d3a095b4ff2b6607d096fa80163/jre-8u131-linux-x64.tar.gz
cd /
tar xfz /tmp/jre-8u131-linux-x64.tar.gz

sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-4.8 50
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-4.8 50

function link_lib() {
	test -e "${1}.0" || die "${1}.0 does not exist"
	test -e "$1" || ln -s "${1}.0" "$1"
}

#link_lib /usr/lib/i386-linux-gnu/libgstinterfaces-0.10.so
#link_lib /usr/lib/i386-linux-gnu/libgstapp-0.10.so
#link_lib /usr/lib/i386-linux-gnu/libgstpbutils-0.10.so
#link_lib /usr/lib/i386-linux-gnu/libgstvideo-0.10.so
link_lib /usr/lib/x86_64-linux-gnu/libgstinterfaces-0.10.so
link_lib /usr/lib/x86_64-linux-gnu/libgstapp-0.10.so
link_lib /usr/lib/x86_64-linux-gnu/libgstpbutils-0.10.so
link_lib /usr/lib/x86_64-linux-gnu/libgstvideo-0.10.so


# Start Jenkins slave
# Todo. Get the URL & secret key automatically
#java -jar slave.jar \
#     -jnlpUrl http://10.0.3.186:8080/computer/ubuntu_14_04/slave-agent.jnlp \
#     -secret 1001701c840b96b10cd05978f865c17fb2bbe9a7ce878b375576497d6cbb825b &

# root directory for manual building:
PROJ_ROOT_DIR=/nx
mkdir -p $PROJ_ROOT_DIR
chown vagrant:vagrant $PROJ_ROOT_DIR

# root directory for jenkins agent
mkdir -p /jenkins
chown vagrant:vagrant /jenkins
