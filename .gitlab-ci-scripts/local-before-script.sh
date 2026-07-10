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
    debian-bullseye)
        # bullseye ships python3.9; motley_cue needs >= 3.10. No official or
        # backports python3.10 exists for bullseye, so use python3.11 from the
        # (unofficial, Debian-developer-maintained) paravoid backports repo.
        echo "installing python3.11 from the paravoid backports repo"
        apt-get update
        apt-get install -y wget gnupg ca-certificates
        install -d /etc/apt/keyrings
        wget -qO - https://people.debian.org/~paravoid/python-all/unofficial-python-all.asc \
            | gpg --dearmor > /etc/apt/keyrings/paravoid-python-all.gpg
        echo "deb [signed-by=/etc/apt/keyrings/paravoid-python-all.gpg] http://people.debian.org/~paravoid/python-all bullseye main" \
            > /etc/apt/sources.list.d/paravoid-python-all.list
        apt-get update
        apt-get install -y python3.11 python3-stdlib-extensions
        # The -venv/-dev subpackages may not be published separately (the
        # python3.11 package bundles the stdlib, incl. venv). Pull them if they
        # exist, but don't fail the build if they don't.
        apt-get install -y python3.11-venv python3.11-dev || true
        # Verify the venv module is usable, since dh_virtualenv --builtin-venv
        # relies on `python3.11 -m venv`.
        python3.11 -m venv --help > /dev/null
        ;;
    ubuntu-focal)
        # focal ships python3.8; motley_cue needs >= 3.10. Install python3.10
        # from the deadsnakes PPA. We add the repo manually (key + sources file)
        # rather than via add-apt-repository, which silently failed to register
        # the PPA in the build container.
        echo "installing python3.10 from the deadsnakes PPA"
        apt-get update
        apt-get install -y gnupg ca-certificates
        install -d /etc/apt/keyrings
        gpg --no-default-keyring --keyring /tmp/deadsnakes-kr.gpg \
            --keyserver keyserver.ubuntu.com \
            --recv-keys F23C5A6CF475977595C89F51BA6932366A755776
        gpg --no-default-keyring --keyring /tmp/deadsnakes-kr.gpg \
            --export > /etc/apt/keyrings/deadsnakes.gpg
        echo "deb [signed-by=/etc/apt/keyrings/deadsnakes.gpg] https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu focal main" \
            > /etc/apt/sources.list.d/deadsnakes.list
        apt-get update
        apt-get install -y python3.10 python3.10-venv python3.10-dev python3.10-distutils
        ;;
esac
echo "END local-before-script.sh #####################################"
