#!/bin/bash

echo "### local-before-script.sh #####################################"
echo -n "find python3 version: "
python3 --version
ls -l `which python3`
ls -l /etc/alternatives/python3*
ls -l /usr/bin/python3*

# Tweak python versions for some distros whose default python3 is too old
# (motley_cue needs >= 3.10; bullseye ships 3.9, focal ships 3.8/3.9).
export DEBIAN_FRONTEND=noninteractive
case "${DISTRO}-${RELEASE}" in
    ubuntu-focal)
        echo "installing python3.10 from the deadsnakes PPA"
        apt-get update
        apt-get install -y software-properties-common
        add-apt-repository -y ppa:deadsnakes/ppa
        apt-get update
        apt-get install -y python3.10 python3.10-venv python3.10-dev python3.10-distutils
        ;;
    debian-bullseye)
        # deadsnakes has no Debian packages, so build 3.10 from source into
        # /usr/local (make altinstall keeps the system python3.9 intact).
        echo "building python3.10 from source"
        PYVER=3.10.16
        apt-get update
        apt-get install -y wget ca-certificates build-essential \
            zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev \
            libreadline-dev libffi-dev libsqlite3-dev libbz2-dev liblzma-dev
        wget -q "https://www.python.org/ftp/python/${PYVER}/Python-${PYVER}.tgz"
        tar xzf "Python-${PYVER}.tgz"
        ( cd "Python-${PYVER}" \
            && ./configure --enable-optimizations --prefix=/usr/local \
            && make -j"$(nproc)" \
            && make altinstall )
        ;;
esac
echo "END local-before-script.sh #####################################"
