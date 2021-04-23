Name: motley-cue
Version: 0.0.13
Release: 1
Summary: Mapper Oidc To Local idEntitY with loCal User managEment
Group: Misc
License: MIT-License
URL: https://git.scc.kit.edu/dianagudu/motley_cue.git
Source0: motley-cue.tar

BuildRequires: python3-setuptools >= 39, python36 >= 3.6, python3-pip >= 9.0, python3-virtualenv >= 15.1, python36-devel >= 3.6

BuildRoot:	%{_tmppath}/%{name}
Requires: python36 >= 3.6, nginx

%define debug_package %{nil}
%define modname motley_cue
%define venv_install /usr/lib/%{name}
%define installroot %{buildroot}%{venv_install}

%description
This tool provides an OIDC-protected REST interface that allows requesting
the creation, deletion, and information of a user-account.

%prep
%setup -q

%build

%install
make install DESTDIR=%{buildroot}
./rpm/fix-venv-paths.sh %{buildroot} %{name}

mkdir -p %{buildroot}{/var/log/%{modname},/run/%{modname},/etc/nginx/conf.d,/lib/systemd/system}
mv %{installroot}/etc/%{modname} %{buildroot}/etc/%{modname}
mv %{installroot}/etc/nginx/nginx.motley_cue %{buildroot}/etc/nginx/conf.d/nginx.motley_cue.conf
mv %{installroot}/etc/systemd/system/motley-cue.service %{buildroot}/lib/systemd/system/

%files
%defattr(-,root,root,-)
%license LICENSE
%dir %{venv_install}
%dir /etc/%{modname}
%dir /var/log/%{modname}
%dir /run/%{modname}
%{venv_install}/*
/etc/%{modname}/*
/etc/nginx/conf.d/nginx.motley_cue.conf
/lib/systemd/system/motley-cue.service

%changelog

%post
SAVED_DIR=`pwd`
    cd %{venv_install}/lib
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
systemctl enable %{name} 
systemctl restart nginx
systemctl restart %{name} 
