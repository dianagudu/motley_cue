Name: motley-cue
Version: 0.7.3
Release: 1%{?dist}

Summary: Mapper Oidc To Local idEntitY with loCal User managEment
Group: Misc
License: MIT
URL: https://github.com/dianagudu/motley_cue
Source0: motley-cue.tar.gz
Patch0: logfiles.patch
Patch1: otp.patch
AutoReq: no

# OpenSUSE likes to have a Group
%if 0%{?suse_version} > 0
Group: System/Libraries
%endif

%if 0%{?centos} == 7
BuildRequires: centos-release-scl-rh, centos-release-scl
BuildRequires: rh-python38 >= 2.0, rh-python38-python-devel >= 3.8
BuildRequires: policycoreutils, policycoreutils-python
%endif
%if 0%{?centos} == 8
# valid for centos stream and rocky linux
BuildRequires: python3.11 >= 3.11, python3.11-devel >= 3.9
BuildRequires: python3-policycoreutils >= 2.9
%endif
%if 0%{?sle_version} == 150500 || 0%{?suse_version} > 1600
# valid for opensuse leap 15.5 and opensuse tumbleweed
BuildRequires: python311 >= 3.11, python311-devel >= 3.11
BuildRequires: python311-pip, python311-setuptools
BuildRequires: python3-policycoreutils >= 3.0
%endif
%if 0%{?sle_version} == 150400
# valid for opensuse leap 15.4
BuildRequires: python311 >= 3.11, python39-devel >= 3.11
BuildRequires: python311-pip, python311-setuptools
BuildRequires: python3-policycoreutils >= 3.0
%endif

BuildRoot:	%{_tmppath}/%{name}
%if 0%{?centos} == 7
Requires: rh-python38 >= 2.0
%endif
%if 0%{?centos} == 8
# valid for centos stream and rocky linux
Requires: python3.11 >= 3.11
%endif
%if 0%{?sle_version} == 150500 || 0%{?suse_version} > 1600
# valid for opensuse leap 15.5 and opensuse tumbleweed
Requires: python311 >= 3.11
%endif
%if 0%{?sle_version} == 150400
# valid for opensuse leap 15.4
Requires: python311 >= 3.11
%endif
Requires: nginx >= 1.16.1

%define debug_package %{nil}
%define modname motley_cue
%define venv_dir /usr/lib/%{name}
%define installroot %{buildroot}%{venv_dir}

%define share_dir /usr/share/%{name}
%define log_dir /var/log/%{modname}
%define etc_dir /etc/%{modname}
%define run_dir /run/%{modname}
%define lib_dir /var/lib/%{modname}
%define cache_dir /var/cache/%{modname}

%description
This tool provides an OIDC-protected REST interface that allows requesting
the creation, deletion, and information of a user-account.

%prep
%setup -q
%patch0 -p1

%build

%install
make install DESTDIR=%{buildroot}
./rpm/fix-venv-paths.sh %{buildroot} %{name} %{_basedir}
./rpm/compile-semodules.sh %{installroot}%{share_dir}/selinux

mkdir -p %{buildroot}{%{etc_dir},%{log_dir},%{run_dir},%{share_dir}/selinux,%{lib_dir},%{cache_dir},/etc/nginx/conf.d,/lib/systemd/system,/usr/sbin,/etc/init.d}
cp -r %{installroot}%{etc_dir}/* %{buildroot}%{etc_dir}/
install %{installroot}%{share_dir}/selinux/* %{buildroot}%{share_dir}/selinux/
install %{installroot}/etc/nginx/nginx.motley_cue %{buildroot}/etc/nginx/conf.d/nginx.motley_cue.conf
install %{installroot}/etc/systemd/system/motley-cue.service %{buildroot}/lib/systemd/system/
install %{installroot}/bin/motley-cue %{buildroot}/usr/sbin/
install %{installroot}/etc/init.d/motley-cue %{buildroot}/etc/init.d/

%files
%defattr(-,root,root,-)
%license LICENSE
%dir %{venv_dir}
%dir %{etc_dir}
%dir %{log_dir}
%dir %{run_dir}
%dir %{lib_dir}
%dir %{cache_dir}
%if 0%{?centos}
%dir %{share_dir}
%endif
%config(noreplace) %{etc_dir}/*
%{venv_dir}/*
%if 0%{?centos}
%{share_dir}/*
%else
%exclude %{share_dir}/*
%endif
%config(noreplace) /etc/nginx/conf.d/nginx.motley_cue.conf
/lib/systemd/system/motley-cue.service
/usr/sbin/motley-cue
/etc/init.d/motley-cue

%changelog

%post
SAVED_DIR=`pwd`
    # LIB 
    cd %{venv_dir}/lib
    PKG_PYTHONDIR=""
    PYTHON3_MAJOR=`python3 --version| cut -d\  -f 2 | cut -d\. -f 1`
    PYTHON3_MINOR=`python3 --version| cut -d\  -f 2 | cut -d\. -f 2`
    for PYTHONDIR in python*; do
        #echo "For loop: PYTHONDIR: ${PYTHONDIR}"
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
    # BIN 
    #cd %{venv_dir}/bin
    
%if 0%{?centos}
cd $SAVED_DIR
(
    semodule -i %{share_dir}/selinux/motley-cue-gunicorn.pp
    semodule -i %{share_dir}/selinux/motley-cue-sshd.pp
    semodule -i %{share_dir}/selinux/motley-cue-nginx.pp
    setsebool -P nis_enabled 1
) || true
%endif
systemctl enable %{name} || update-rc.d %{name} defaults || true
systemctl restart %{name} || service %{name} restart || /etc/init.d/motley-cue restart || true
systemctl restart nginx || service nginx restart || nginx -s reload || nginx || true

%preun
echo "Preun: $0 $1"
if [ $1 -eq 0 ] ; then
    echo "Removing package"
    systemctl stop %{name} || service %{name} stop || /etc/init.d/motley-cue stop || true
    systemctl disable %{name} || update-rc.d -f %{name} remove || true
fi

%postun
echo "Postun: $0 $1"
# Only run on uninstall
if [ $1 = 0 ]; then
    echo "postun uninstall"
    # remove any remaining filed (e.g. the virtualenv, caches, logs, etc)
    rm -rf %{venv_dir}
    rm -rf %{etc_dir}
    rm -rf %{log_dir}
    rm -rf %{run_dir}
    rm -rf %{lib_dir}
    rm -rf %{cache_dir}
    %if 0%{?centos}
    (
        semodule -r motley-cue-gunicorn
        semodule -r motley-cue-sshd
        semodule -r motley-cue-nginx
        setsebool -P nis_enabled 0
    ) || true
    %endif
fi
# also on upgrade, i.e. $1 == 2
systemctl restart nginx || service nginx restart || nginx -s reload || nginx || true
