Name: motley-cue
Version: 0.0.9
Release: 1
Summary: Mapper Oidc To Local idEntitY with loCal User managEment
Group: Misc
License: MIT-License
URL: https://git.scc.kit.edu:fum/fum_ldf-interface.git
Source0: motley-cue.tar

BuildRequires: python3-setuptools >= 39, python36 >= 3.6, python3-pip >= 9.0, python3-virtualenv >= 15.1, python36-devel >= 3.6

BuildRoot:	%{_tmppath}/%{name}

%define debug_package %{nil}

%description
This tool provides an OIDC-protecte REST interface that allows requesting
the creation, deletion, and information of a user-account.

%prep
%setup -q

%build
#make virtualenv DESTDIR=${RPM_BUILD_ROOT}

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

%files
%defattr(-,root,root,-)
/usr/*
/lib/*
/bin/*

%changelog

