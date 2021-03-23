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
    apt-get update
    apt-get -y install software-properties-common
    add-apt-repository -y ppa:jyrki-pulliainen/dh-virtualenv

    apt-get update
    apt-get -y install dh-virtualenv
}

cd /home/build/$PACKAGE 
mkdir -p $OUTPUT/$DIST

case "$DIST" in
    debian_buster|debian_bullseye|debian_stretch|ubuntu_bionic)
        debian_install_dependencies
        debian_build_package
        debian_copy_output
    ;;
    ubuntu_focal)   
        ubuntu_focal_install_dependencies
        debian_install_dependencies
        debian_build_package
        debian_copy_output
    ;;
esac



