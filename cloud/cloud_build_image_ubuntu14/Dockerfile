FROM ubuntu:14.04

RUN apt-get update && apt-get install -y vim strace
RUN apt-get update && apt-get install -y libglib2.0
RUN apt-get install -y software-properties-common && add-apt-repository ppa:ubuntu-toolchain-r/test && apt-get update && apt-get install -y libstdc++6 gdb curl
RUN apt-get update && apt-get install -y libgl1-mesa-glx
RUN ulimit -c unlimited
RUN echo '* hard core unlimited' >> /etc/security/limits.conf 
RUN echo '* soft core unlimited' >> /etc/security/limits.conf 
RUN echo 'kernel.core_pattern=core.%e.%p.%h.%t' >> /etc/sysctl.conf
RUN apt-get update && apt-get install -y net-tools
RUN apt-get update && apt-get install -y less
RUN apt-get update && apt-get install -y g++-7
RUN apt-get update && apt-get install -y wget curl
RUN ln -sf /usr/bin/g++-7 /usr/bin/g++ && ln -sf /usr/bin/gcc-7 /usr/bin/gcc
RUN cd /tmp && wget https://cmake.org/files/v3.11/cmake-3.11.1.tar.gz && tar xf cmake-3.11.1.tar.gz
RUN apt-get update && apt-get install -y make ninja-build
RUN cd /tmp/cmake-3.11.1 && ./bootstrap --prefix=/usr && make -j 10 && make install
RUN apt-get update && apt-get install -y rsync default-jre
RUN apt-get update && apt-get install -y python-pip python3-pip
RUN ln -sf /usr/bin/g++-7 /usr/bin/g++ && ln -sf /usr/bin/gcc-7 /usr/bin/gcc
RUN apt-get install -y libxml2-dev libxslt-dev python-dev lib32z1-dev libyaml-dev mercurial python-dev python3-dev xsltproc libxml2-dev
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash -
RUN apt-get install -y nodejs
