#!/bin/bash

### Build using:

#DIST=ubuntu_bionic ; docker run -it --rm -v `dirname $PWD`:/home/build $DIST /home/build/`basename $PWD`/build.sh `basename $PWD` $DIST $PKG_NAME

## ASSUMPTION: /home/build/$PACKAGE holds the sources for the package to be built
## ASSUMPTION: /home/build is on the host system.
## PKG_NAME is optional, defaults to $PACKAGE when not given

BASE="/home/build"
PACKAGE=$1
DIST=$2
OUTPUT="$BASE/results"
PKG_NAME=$3

test -z $PKG_NAME && {
    echo "Package name not specified, using $PACKAGE"
    PKG_NAME=$PACKAGE
}

echo "PACKAGE: $PACKAGE"
echo "DIST: $DIST"
echo "PKG_NAME: $PKG_NAME"

test -z $DIST && {
    echo "Must specify DIST as 2nd parameter"
    exit
}

common_prepare_dirs() {
    mkdir -p /tmp/build
    mkdir -p $OUTPUT/$DIST
    cp -af $BASE/$PACKAGE /tmp/build
    cd /tmp/build/$PACKAGE 
}
common_fix_output_permissions() {
    UP_UID=`stat -c '%u' $BASE`
    UP_GID=`stat -c '%g' $BASE`
    chown $UP_UID:$UP_GID $OUTPUT
    chown -R $UP_UID:$UP_GID $OUTPUT/$DIST
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
    ls -l ..
    mv ../${PKG_NAME}_[0-9]* $OUTPUT/$DIST
    mv ../${PKG_NAME}-dbgsym_* $OUTPUT/$DIST 2>/dev/null
}
ubuntu_focal_install_dependencies() {
    apt-get update
    apt-get -y install software-properties-common
    add-apt-repository -y ppa:jyrki-pulliainen/dh-virtualenv

    apt-get update
    apt-get -y install dh-virtualenv
}

centos8_install_dependencies() {
    yum -y install python3 python3-devel python3-pip python3-setuptools \
        python3-virtualenv python3-pip
    pip3 install -U pip
}
rpm_build_package() {
    cd /tmp/build/$PACKAGE 
    #make srctar
    make rpm
}
rpm_copy_output() {
    ls -l rpm/rpmbuild/RPMS/*/*
    echo "-----"
    mv rpm/rpmbuild/RPMS/*/*rpm $OUTPUT/$DIST
}

###########################################################################
common_prepare_dirs

case "$DIST" in
    debian_buster|debian_bullseye|ubuntu_bionic)
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
    centos8)
        centos8_install_dependencies
        rpm_build_package
        rpm_copy_output
    ;;
esac

common_fix_output_permissions
