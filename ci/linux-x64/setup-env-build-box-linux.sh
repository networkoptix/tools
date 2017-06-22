#!/bin/bash -xe

NX_RSYNC_SOURCE=enk.me
OS=linux
ARCH=x64

PROJ_ROOT_DIR=/nx
BUILDENV_DIR=$PROJ_ROOT_DIR/buildenv

CMAKE_VERSION=3.8.2
CMAKE_DIR_NAME=cmake-$CMAKE_VERSION-Linux-x86_64
CMAKE_ARCH_NAME=$CMAKE_DIR_NAME.tar.gz

mkdir -p $PROJ_ROOT_DIR

cat > $HOME/.profile <<EOF
. \$HOME/.bashrc
export PATH=$HOME/$CMAKE_DIR_NAME/bin:$PATH:$BUILDENV_DIR/bin:$BUILDENV_DIR/qt/bin:$BUILDENV_DIR/maven/bin
export QTDIR=$BUILDENV_DIR/qt
export ANDROID_NDK_ROOT=$BUILDENV_DIR/android/android-ndk
export ANDROID_SDK_ROOT=$BUILDENV_DIR/android/android-sdk
export environment=$BUILDENV_DIR
EOF

# key for read-only access to mercury repositories
cat > $HOME/.ssh/id_rsa <<EOF
-----BEGIN RSA PRIVATE KEY-----
MIICWQIBAAKBgGkJ6s8fQsG7HfkeU5cBO1khesW2hJeJxk7EUgIfiBNP5omAbsJA
1YPZyhlAs1KiiqVSXnpJIo8DVls4XlUirAv89j+p/4JFk3Vbo4H1IEnrUrB/wlrM
ZW30HvYYZfDhzHRjpiikLaBfSZSZyNm9UhWOJ1AX3aS7FagcYCfMYT/3AgElAoGA
KpVRWuMo5sF62p2XgmhIfhR94XOB3JHM74AFkih1b5zuwh9Pfy8Kc7koaxo63E+7
qs5dpzJn9MoAaiub3VM+0+hNsOh7CvujN16w7+/RrXh+9E1PYY0tjqKpJr2qoS5C
IIGjFjmARiGckQoC4OwOWeFafDte8wV1mixRSQQ4uU0CQQCtc64UWdOVv/aGH9/+
Bnss4TIGq803e/dc0eUN/si7kDI1fATJSlgYpm9G6jCOSXYYBMeoTvT1gsKys6hR
ap3HAkEAmwcyi2UcIPyg6/FSHwOJP+MBumPQJ5s44/AX4Tm8tCGtuzF1kVGKN/7Q
oJNLLQdbW1RnEE8lHoHglfUPo8AMUQJAWRHjxULiRfrKs5PT409vr0M1XV8kMT+o
iZw3Wja6GyCIfFRxKRhWwIzRW8ReH42B1PuJHxPJ5dtdD6hdWj2q9wJAHVRjgifi
uiH07l4WdJH3Xx0cAKsZivPaVKMLb8ynKP9z5SUIZ5nOCpf99N2YmdD1m6gvLJla
DLDJn9Rqvh1qHQJBAJEoue5ik0Iaob7Yc+86WaTAxljr35BwZfFtpvwDVLf0wy7E
DsyOb5b5w2JkqKvY+IoCso+iW76HLdi73UY4Luw=
-----END RSA PRIVATE KEY-----
EOF
chmod 600 $HOME/.ssh/id_rsa

# prevent from ssh asking "Are you sure you want to continue connecting (yes/no)?"
ssh-keyscan $NX_RSYNC_SOURCE >> ~/.ssh/known_hosts

cd $PROJ_ROOT_DIR
test -e buildenv || hg clone ssh://hg@$NX_RSYNC_SOURCE/buildenv
test -e devtools || hg clone ssh://hg@$NX_RSYNC_SOURCE/devtools

cd $BUILDENV_DIR
rsync -a --delete rsync://$NX_RSYNC_SOURCE/buildenv/all-os/help .
#rsync -a --delete rsync://$NX_RSYNC_SOURCE/buildenv/all-os/qt5/src qt5  # No such file or directory
rsync -a rsync://$NX_RSYNC_SOURCE/buildenv/all-os/ . --exclude 'help' --exclude 'qt5'
rsync -a rsync://$NX_RSYNC_SOURCE/buildenv/$OS/noarch/ .
rsync -a rsync://$NX_RSYNC_SOURCE/buildenv/$OS/$ARCH/ .

# download and unpack cmake
cd /tmp
wget --no-verbose https://cmake.org/files/v3.8/$CMAKE_ARCH_NAME
cd ~/
tar xfz /tmp/$CMAKE_ARCH_NAME
