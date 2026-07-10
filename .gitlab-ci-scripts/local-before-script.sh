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
    debian-bullseye|ubuntu-focal)
        # Neither distro ships python3.10 and deadsnakes has no Debian packages
        # (and its PPA is unreliable in the focal build container), so build
        # 3.10 from source into /usr/local. "make altinstall" keeps the system
        # python3 (3.9) intact, so apt's python tooling is not disturbed.
        echo "building python3.10 from source for ${DISTRO}-${RELEASE}"
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
