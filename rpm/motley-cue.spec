Name: motley-cue
Version: 0.0.12
Release: 2
Summary: Mapper Oidc To Local idEntitY with loCal User managEment
Group: Misc
License: MIT-License
URL: https://git.scc.kit.edu:fum/fum_ldf-interface.git
Source0: motley-cue.tar

BuildRequires: python3-setuptools >= 39, python36 >= 3.6, python3-pip >= 9.0, python3-virtualenv >= 15.1, python36-devel >= 3.6

BuildRoot:	%{_tmppath}/%{name}
Requires: nginx

%define debug_package %{nil}

%description
This tool provides an OIDC-protected REST interface that allows requesting
the creation, deletion, and information of a user-account.

%prep
%setup -q

%build
#make virtualenv DESTDIR=${RPM_BUILD_ROOT}

#%clean
#rm -rf %{buildroot}

%install
echo "Buildroot: ${RPM_BUILD_ROOT}"
echo "ENV: "
env | grep -i rpm
echo "PWD"
pwd
#make install INSTALL_PATH=${RPM_BUILD_ROOT}/usr MAN_PATH=${RPM_BUILD_ROOT}/usr/share/man CONFIG_PATH=${RPM_BUILD_ROOT}/etc
#make virtualenv DESTDIR=/tmp/build/motley_cue/rpm/rpmbuild/BUILD/motley-cue-0.0.9-1.x86_64
#make install DESTDIR=/tmp/build/motley_cue/rpm/rpmbuild/BUILD/motley-cue-0.0.9-1.x86_64
make virtualenv DESTDIR=${RPM_BUILD_ROOT}
make install DESTDIR=${RPM_BUILD_ROOT}
make fix-venv-path DESTDIR=${RPM_BUILD_ROOT}

%files
%defattr(-,root,root,-)
/usr/lib/motley*
/lib/*
/bin/*
/etc/*

%changelog

%post
SAVED_DIR=`pwd`
    cd /usr/lib/motley-cue/lib
    PKG_PYTHONDIR=""
    PYTHON3_MAJOR=`python3 --version| cut -d\  -f 2 | cut -d\. -f 1`
    PYTHON3_MINOR=`python3 --version| cut -d\  -f 2 | cut -d\. -f 2`
    for PYTHONDIR in python*; do
        test -e $PYTHONDIR && {
            test -L $PYTHONDIR || {
                # If it exists but is not a symlink, then we found the
                # Python dir for the version this package was created for
                PKG_PYTHONDIR=$PYTHONDIR
                #echo "PKG_PYTHONDIR: $PKG_PYTHONDIR"
            } || true
        } || true
    done
    test -z $PKG_PYTHONDIR && {
        echo "Can not find python package dir"
        exit 44
    }
    if [ "x${PKG_PYTHONDIR}" = "xpython${PYTHON3_MAJOR}.${PYTHON3_MINOR}" ] ; then
        echo -n ""
    else
        echo "Package was packed for $PKG_PYTHONDIR adjusting symlinks for installed python${PYTHON3_MAJOR}.${PYTHON3_MINOR}"
        test -e python${PYTHON3_MAJOR}.${PYTHON3_MINOR} || {
            ln -s $PKG_PYTHONDIR python${PYTHON3_MAJOR}.${PYTHON3_MINOR}
        }
    fi
cd $SAVED_DIR
systemctl enable nginx
systemctl enable motley_cue 
systemctl restart nginx
systemctl restart motley_cue 
