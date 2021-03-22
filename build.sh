#!/bin/bash

### Build using:
# DIST=debian_bullseye 
# docker run -it --rm -v `dirname $PWD`:/home/build $DIST /home/build/motley_cue/build.sh `basename $PWD` $DIST
# DIST=ubuntu_bionic; # docker run -it --rm -v `dirname $PWD`:/home/build $DIST /home/build/`basename $PWD`/build.sh `basename $PWD` $DIST

PACKAGE=$1
DIST=$2
OUTPUT="../results"

echo "PACKAGE: $PACKAGE"
echo "DIST: $DIST"

test -z $DIST && {
    echo "Must specify DIST as 2nd parameter"
    exit
}

debian_install_dependencies() {
    apt-get -y install libffi-dev  \
        python3 python3-dev python3-pip python3-setuptools
    }
debian_build_package() {
    make debsource && \
    dpkg-buildpackage -uc -us
}

debian_copy_output() {
    mv ../motley-cue_* $OUTPUT/$DIST
    mv ../motley-cue-dbgsym_* $OUTPUT/$DIST
}
ubuntu_focal_install_dependencies() {
    #echo "deb http://archive.ubuntu.com/ubuntu/ bionic universe" >>\
    #    /etc/apt/sources.list
    apt-get update
    apt-get -y install software-properties-common
    add-apt-repository -y ppa:jyrki-pulliainen/dh-virtualenv

    #echo -e "APT::Default-Release "focal";\nAPT::Cache-Limit 500000000;\nApt::Get::Purge;" \
    #   >> /etc/apt/apt.conf.d/30defaultrelease
    ## Add debian keys:
    #gpg --no-default-keyring \
    #    --keyring /usr/share/keyrings/build-keyring.gpg \
    #    --recv-keys --keyserver ipv4.pool.sks-keyservers.net \
    #    04EE7237B7D453EC 648ACFD622F3D138
    #    gpg --export 04EE7237B7D453EC | apt-key add -
    #    gpg --export 648ACFD622F3D138 | apt-key add -
    apt-get update
    apt-get -y install dh-virtualenv

}
ubuntu_xenial_debian_compat_create() {
    echo 10 > debian/compat
}
ubuntu_xenial_debian_compat_remove() {
    rm debian/compat
}

cd /home/build/$PACKAGE 
mkdir -p $OUTPUT/$DIST

case "$DIST" in
    debian_buster|debian_bullseye|debian_stretch|ubuntu_bionic)
        debian_install_dependencies
        debian_build_package
        debian_copy_output
    ;;
    ubuntu_xenial)
        ubuntu_xenial_debian_compat_create
        ubuntu_focal_install_dependencies
        debian_install_dependencies
        debian_build_package
        ubuntu_xenial_debian_compat_remove
        debian_copy_output
    ;;
    ubuntu_focal)   
        ubuntu_focal_install_dependencies
        debian_install_dependencies
        debian_build_package
        debian_copy_output
    ;;
esac



