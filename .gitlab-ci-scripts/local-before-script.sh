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
        # backports python3.10 exists for bullseye, so use the (third-party)
        # pascalroeleven backport repo, which ships a full 3.10 package set
        # (python3.10 + -venv + -dev) that coexists with the system python3.9.
        echo "installing python3.10 from the pascalroeleven backports repo"
        apt-get update
        apt-get install -y wget ca-certificates
        install -d /etc/apt/keyrings
        wget -qO /etc/apt/keyrings/pascalroeleven.gpg \
            https://pascalroeleven.nl/deb-pascalroeleven.gpg
        echo "deb [signed-by=/etc/apt/keyrings/pascalroeleven.gpg] http://deb.pascalroeleven.nl/python3.10 bullseye-backports main" \
            > /etc/apt/sources.list.d/pascalroeleven.list
        apt-get update
        apt-get install -y python3.10 python3.10-venv python3.10-dev
        # dh_virtualenv --builtin-venv relies on `python3.10 -m venv`.
        python3.10 -m venv --help > /dev/null
        ;;
    ubuntu-focal)
        # focal ships python3.8; motley_cue needs >= 3.10. Install python3.10
        # from the deadsnakes PPA. We add the repo manually (key + sources file)
        # rather than via add-apt-repository, which silently failed to register
        # the PPA in the build container.
        echo "installing python3.10 from the deadsnakes PPA"
        apt-get update
        apt-get install -y wget ca-certificates
        install -d /etc/apt/keyrings
        # Fetch the deadsnakes PPA signing key over HTTPS as an armored file and
        # reference it via signed-by. This avoids gpg --recv-keys, which needs
        # dirmngr and a writable ~/.gnupg (both absent in the build container).
        wget -qO /etc/apt/keyrings/deadsnakes.asc \
            "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xF23C5A6CF475977595C89F51BA6932366A755776"
        echo "deb [signed-by=/etc/apt/keyrings/deadsnakes.asc] https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu focal main" \
            > /etc/apt/sources.list.d/deadsnakes.list
        apt-get update
        apt-get install -y python3.10 python3.10-venv python3.10-dev python3.10-distutils
        ;;
esac
echo "END local-before-script.sh #####################################"
