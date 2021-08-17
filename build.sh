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

echo "PACKAGE=$PACKAGE"
echo "DIST=$DIST"
echo "PKG_NAME=$PKG_NAME"

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
    apt-get update
    apt-get -y install libffi-dev  \
        python3 python3-dev python3-pip python3-setuptools
}
debian_build_package() {
    make debsource && \
    dpkg-buildpackage -uc -us
}

debian_copy_output() {
    echo "Moving output:"
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
        python3-virtualenv python3-pip python3-policycoreutils
    pip3 install -U pip
}
centos7_install_dependencies() {
    yum -y install python3 python3-devel python3-pip python3-setuptools \
        python3-pip policycoreutils-python
    pip3 install -U pip
    pip3 install virtualenv
}
opensuse15_install_dependencies() {
    zypper -n install libcurl-devel pam-devel zypper audit-devel git \
        python3 python3-devel python3-pip python3-setuptools
    zypper -n install python3-pip
    zypper -n install policycoreutils
    zypper -n install policycoreutils-python
    pip3 install -U pip
    pip3 install virtualenv || {
        /usr/local/bin/pip3 install virtualenv
    }
}
centos7_patch_rpm() {
    # Force RPM's python-bytecompile script to use python3
    sed "s@^default_python@default_python=/usr/bin/python3\n#default_python@" -i /usr/lib/rpm/brp-python-bytecompile
    echo "typing-extensions" >> requirements.txt
}
rpm_build_package() {
    cd /tmp/build/$PACKAGE 
    make rpms
}
rpm_copy_output() {
    ls -l rpm/rpmbuild/RPMS/*/*
    ls -l rpm/rpmbuild/SRPMS/
    echo "-----"
    mv rpm/rpmbuild/RPMS/x86_64/${PKG_NAME}*rpm $OUTPUT/$DIST/
    mv rpm/rpmbuild/SRPMS/*rpm $OUTPUT/$DIST
}

###########################################################################
common_prepare_dirs

case "$DIST" in
    debian_buster|debian_bullseye|ubuntu_bionic|debian_bookworm)
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
    centos7)
        centos7_install_dependencies
        centos7_patch_rpm
        rpm_build_package
        rpm_copy_output
    ;;
    centos8)
        centos8_install_dependencies
        rpm_build_package
        rpm_copy_output
    ;;
    opensuse15*|opensuse_tumbleweed|sle*)
        opensuse15_install_dependencies
        rpm_build_package
        rpm_copy_output
    ;;
esac

common_fix_output_permissions
