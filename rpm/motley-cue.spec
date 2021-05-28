Name: motley-cue
%define ver %(head debian/changelog -n 1|cut -d \\\( -f 2|cut -d \\\) -f 1|cut -d \- -f 1)
%define rel %(head debian/changelog -n 1|cut -d \\\( -f 2|cut -d \\\) -f 1|cut -d \- -f 2)
Version: %{ver}
Release: %{rel}

Summary: Mapper Oidc To Local idEntitY with loCal User managEment
Group: Misc
License: MIT
URL: https://github.com/dianagudu/motley_cue
Source0: motley-cue.tar.gz
Patch0: logfiles.patch
AutoReq: no

# OpenSUSE likes to have a Group
%if 0%{?suse_version} > 0
Group: System/Libraries
%endif

%if 0%{?centos} == 7
BuildRequires: python3-setuptools >= 39, python36 >= 3.6, python3-pip >= 9.0, python36-devel >= 3.6
BuildRequires: policycoreutils-python
%endif
%if 0%{?centos} == 8
BuildRequires: python3-setuptools >= 39, python36 >= 3.6, python3-pip >= 9.0, python36-devel >= 3.6
BuildRequires: python3-policycoreutils >= 2.9, python3-virtualenv >= 15.1
%endif
%if 0%{?suse_version}
BuildRequires: python3 >= 3.6 python3-policycoreutils >= 2.9
#, python3-virtualenv >= 15.1
%endif

BuildRoot:	%{_tmppath}/%{name}
%if 0%{?centos}
Requires: python36 >= 3.6
%endif
%if 0%{?suse_version}
Requires: python3 >= 3.6
%endif
Requires: nginx >= 1.16.1

%define debug_package %{nil}
%define modname motley_cue
%define venv_dir /usr/lib/%{name}
%define installroot %{buildroot}%{venv_dir}

%define se_dir /usr/share/%{name}/selinux
%define log_dir /var/log/%{modname}
%define etc_dir /etc/%{modname}
%define run_dir /run/%{modname}

%description
This tool provides an OIDC-protected REST interface that allows requesting
the creation, deletion, and information of a user-account.

%prep
%setup -q
%patch0 -p1

%build

%install
%if 0%{?centos} == 7
export PYTHONPATH=/usr/local/lib/python3.6/site-packages
%endif
make install DESTDIR=%{buildroot}
./rpm/fix-venv-paths.sh %{buildroot} %{name}
./rpm/compile-semodules.sh %{installroot}%{se_dir}

mkdir -p %{buildroot}{%{etc_dir},%{log_dir},%{run_dir},%{se_dir},/etc/nginx/conf.d,/lib/systemd/system}
install %{installroot}%{etc_dir}/* %{buildroot}%{etc_dir}/
install %{installroot}%{se_dir}/* %{buildroot}%{se_dir}/
install %{installroot}/etc/nginx/nginx.motley_cue %{buildroot}/etc/nginx/conf.d/nginx.motley_cue.conf
install %{installroot}/etc/systemd/system/motley-cue.service %{buildroot}/lib/systemd/system/

%files
%defattr(-,root,root,-)
%license LICENSE
%dir %{venv_dir}
%dir %{etc_dir}
%dir %{log_dir}
%dir %{run_dir}
%if 0%{?centos}
%dir %{se_dir}
%endif
%{venv_dir}/*
%config(noreplace) %{etc_dir}/*
%if 0%{?centos}
%{se_dir}/*
%else
%exclude %{se_dir}/*
%endif
/etc/nginx/conf.d/nginx.motley_cue.conf
/lib/systemd/system/motley-cue.service

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
    semodule -i %{se_dir}/motley-cue-gunicorn.pp
    semodule -i %{se_dir}/motley-cue-sshd.pp
    semodule -i %{se_dir}/motley-cue-nginx.pp
    setsebool -P nis_enabled 1
) || true
%endif
systemctl enable %{name} nginx
systemctl restart %{name} nginx

%postun
echo "Postun: $0 $1"
# Only run on uninstall
if [ $1 = 0 ]; then
    echo "postun uninstall"
    %if 0%{?centos}
    (
        semodule -r motley-cue-gunicorn
        semodule -r motley-cue-sshd
        semodule -r motley-cue-nginx
        setsebool -P nis_enabled 0
    ) || true
    %endif
fi
systemctl restart nginx
