PKG_NAME  = motley-cue
PKG_NAME_UNDERSCORES  = motley_cue

SPECFILE := rpm/${PKG_NAME}.spec
RPM_VERSION := $(shell grep ^Version ${SPECFILE} | cut -d : -f 2 | sed s/\ //g)

BASE_VERSION := $(shell head debian/changelog  -n 1 | cut -d \( -f 2 | cut -d \) -f 1 | cut -d \- -f 1)
DEBIAN_VERSION := $(shell head debian/changelog  -n 1 | cut -d \( -f 2 | cut -d \) -f 1 | sed s/-[0-9][0-9]*//)
VERSION := $(DEBIAN_VERSION)

# Parallel builds:
MAKEFLAGS += -j5

BASEDIR = $(PWD)
BASENAME := $(notdir $(PWD))
DOCKER_BASE=`dirname ${PWD}`
PACKAGE=`basename ${PWD}`
SRC_TAR:=$(PKG_NAME).tar.gz

SHELL:=bash

# Python interpreter used to build the bundled virtualenv (rpm/install targets).
# EL8 and openSUSE Leap ship an ancient default python3 (3.6), so when a newer
# interpreter has been installed explicitly (python3.11, matching the spec's
# BuildRequires) we prefer it; everywhere else (EL9/EL10, Fedora, Tumbleweed,
# Debian/Ubuntu) the distro default python3 is recent enough.
# Override on the command line with e.g.: make PYTHON=python3.12 rpms
PYTHON ?= $(shell command -v python3.11 >/dev/null 2>&1 && echo python3.11 || echo python3)

info:
	@echo "############################################################"
	@echo "DESTDIR:         $(DESTDIR)"
	@echo "INSTALLDIRS:     $(INSTALLDIRS)"
	@echo "VERSION:         $(VERSION)"
	@echo "RPM_VERSION:     $(RPM_VERSION)"
	@echo "DEBIAN_VERSION:  $(DEBIAN_VERSION)"
	@echo "BASE_VERSION:    ${BASE_VERSION}"
	@echo "BASEDIR: ${BASEDIR}"
	@echo "############################################################"

### Actual targets
default: sdist bdist_wheel

sdist:
	python3 -m build --sdist
bdist_wheel:
	python3 -m build --wheel

dist: sdist bdist_wheel

clean: cleandist
	rm -rf build 
	rm -rf doc/build
	rm -rf *.egg-info
	rm -rf .eggs
	rm -rf htmlcov coverage.svg coverage.locv

distclean: clean
	rm -rf .tox
	rm -rf venv
	rm -rf .pytest_cache
	find -type d -name __pycache__ | xargs rm -rf 
	rm -rf rpm/rpmbuild
	./debian/rules clean

cleandist:
	rm -rf dist

twine: cleandist sdist bdist_wheel
	twine upload dist/*

stwine: cleandist sdist bdist_wheel
	# Fixme: The key id is hardcoded
	twine upload -s -i 98C39659EFE29F20D3A9915A2EDADFE848C31452 dist/* 

docs:
	tox -e docs

tox:
	tox -e py39

# Dockers
.PHONY: dockerised_some_packages
dockerised_some_packages: dockerised_deb_debian_buster\
	dockerised_rpm_rocky8.5\

.PHONY: dockerised_most_packages
dockerised_most_packages: dockerised_deb_debian_buster\
	dockerised_deb_debian_bookworm\
	dockerised_deb_debian_trixie\
	dockerised_rpm_centos7\
	dockerised_rpm_centos_stream\
	dockerised_rpm_rocky8.5\
	dockerised_rpm_rocky8\
	dockerised_rpm_opensuse_tumbleweed\

.PHONY: dockerised_all_packages
dockerised_all_packages: dockerised_deb_debian_buster\
	dockerised_deb_debian_bullseye\
	dockerised_deb_debian_bookworm\
	dockerised_deb_ubuntu_focal\
	dockerised_deb_ubuntu_jammy\
	dockerised_deb_ubuntu_noble\
	dockerised_deb_ubuntu_resolute\
	dockerised_rpm_centos7\
	dockerised_rpm_centos8\
	dockerised_rpm_centos_stream\
	dockerised_rpm_rocky8.5\
	dockerised_rpm_rocky8\
	dockerised_rpm_opensuse15.4\
	dockerised_rpm_opensuse15.5\
	dockerised_rpm_opensuse_tumbleweed

.PHONY: docker_images
docker_images: docker_rocky8.5\
	docker_rocky8\
	docker_centos7\
	docker_centos8\
	docker_centos_stream\
	docker_debian_bullseye\
	docker_debian_buster\
	docker_debian_bookworm\
	docker_ubuntu_focal\
	docker_ubuntu_jammy\
	docker_ubuntu_noble\
	docker_ubuntu_resolute\
	docker_opensuse15.4\
	docker_opensuse15.5\
	docker_opensuse_tumbleweed

.PHONY: docker_debian_buster
docker_debian_buster:
	@echo -e "\ndebian_buster"
	@echo -e "FROM debian:buster\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv dh-virtualenv python3-venv devscripts git "\
    	"python3 python3-dev python3-pip python3-setuptools " | \
	docker build --tag debian_buster -f - .  >> docker.log
.PHONY: docker_debian_bullseye
docker_debian_bullseye:
	@echo -e "\ndebian_bullseye"
	@echo -e "FROM debian:bullseye\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv dh-virtualenv python3-venv devscripts git "\
		"python3 python3-dev python3-pip python3-setuptools "| \
	docker build --tag debian_bullseye -f - .  >> docker.log
.PHONY: docker_debian_bookworm
docker_debian_bookworm:
	@echo -e "\ndebian_bookworm"
	@echo -e "FROM debian:bookworm\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv dh-virtualenv python3-venv devscripts git "\
		"python3 python3-dev python3-pip python3-setuptools "| \
	docker build --tag debian_bookworm -f - .  >> docker.log
.PHONY: docker_debian_trixie
docker_debian_trixie:
	@echo -e "\ndebian_trixie"
	@echo -e "FROM debian:trixie\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv dh-virtualenv python3-venv devscripts git "\
		"python3 python3-dev python3-pip python3-setuptools "| \
	docker build --tag debian_trixie -f - .  >> docker.log
.PHONY: docker_ubuntu_bionic
docker_ubuntu_bionic:
	@echo -e "\nubuntu_bionic"
	@echo -e "FROM ubuntu:bionic\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"dh-virtualenv devscripts git "\
		"python3.8 python3.8-dev python3.8-venv python3-pip "| \
	docker build --tag ubuntu_bionic -f - .  >> docker.log
.PHONY: docker_ubuntu_jammy
docker_ubuntu_jammy:
	@echo -e "\nubuntu_jammy"
	@echo -e "FROM ubuntu:jammy\n"\
	"ENV DEBIAN_FRONTEND=noninteractive\n"\
	"ENV  TZ=Europe/Berlin\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv python3-venv devscripts git "\
		"python3 python3-dev python3-pip python3-setuptools "| \
	docker build --tag ubuntu_jammy -f - .  >> docker.log
.PHONY: docker_ubuntu_noble
docker_ubuntu_noble:
	@echo -e "\nubuntu_noble"
	@echo -e "FROM ubuntu:noble\n"\
	"ENV DEBIAN_FRONTEND=noninteractive\n"\
	"ENV  TZ=Europe/Berlin\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv python3-venv devscripts git "\
		"python3 python3-dev python3-pip python3-setuptools "| \
	docker build --tag ubuntu_noble -f - .  >> docker.log
.PHONY: docker_ubuntu_resolute
docker_ubuntu_resolute:
	@echo -e "\nubuntu_resolute"
	@echo -e "FROM ubuntu:resolute\n"\
	"ENV DEBIAN_FRONTEND=noninteractive\n"\
	"ENV  TZ=Europe/Berlin\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv python3-venv devscripts git "\
		"python3 python3-dev python3-pip python3-setuptools "| \
	docker build --tag ubuntu_resolute -f - .  >> docker.log
.PHONY: docker_centos7
docker_centos7:
	@echo -e "\ncentos7"
	@echo -e "FROM centos:7\n"\
	"RUN yum -y install make rpm-build\n"\
	"RUN yum -y groups mark convert\n"\
	"RUN yum -y groupinstall \"Development tools\"\n" | \
	docker build --tag centos7 -f - .  >> docker.log
.PHONY: docker_centos8
docker_centos8:
	@echo -e "\ncentos8"
	@echo -e "FROM centos:8\n"\
	"RUN sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-Linux-*\n"\
	"RUN sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-Linux-*\n"\
	"RUN yum install -y wget epel-release\n"\
	"RUN yum -y install make rpm-build\n"\
	"RUN yum -y groupinstall \"Development tools\"\n"\
	"RUN dnf -y install https://rpms.remirepo.net/enterprise/remi-release-8.rpm\n"\
	"RUN dnf config-manager --set-enabled powertools\n" | \
	docker build --tag centos8 -f - .  >> docker.log
.PHONY: docker_centos_stream
docker_centos_stream:
	@echo -e "\ncentos_stream"
	@echo -e "FROM tgagor/centos-stream\n"\
	"RUN yum install -y make rpm-build\n" \
	"RUN dnf -y group install \"Development Tools\"\n" | \
	docker build --tag centos_stream -f -  .  >> docker.log
.PHONY: docker_rocky8.5
docker_rocky8.5:
	@echo -e "\nrocky8.5"
	@echo -e "FROM rockylinux:8.5\n"\
	"RUN yum install -y make rpm-build\n" \
	"RUN dnf -y group install \"Development Tools\"\n" | \
	docker build --tag rocky8.5 -f -  .  >> docker.log
.PHONY: docker_rocky8
docker_rocky8:
	@echo -e "\nrocky8"
	@echo -e "FROM rockylinux:8\n"\
	"RUN yum install -y make rpm-build\n" \
	"RUN dnf -y group install \"Development Tools\"\n" | \
	docker build --tag rocky8 -f -  .  >> docker.log
.PHONY: docker_opensuse15.4
docker_opensuse15.4:
	@echo -e "\nopensuse-15.4"
	@echo -e "FROM registry.opensuse.org/opensuse/leap:15.4\n"\
	"RUN zypper -n install make rpm-build\n" \
	"RUN zypper -n install -t pattern devel_C_C++" | \
	docker build --tag opensuse15.4 -f -  .  >> docker.log
.PHONY: docker_opensuse15.5
docker_opensuse15.5:
	@echo -e "\nopensuse-15.5"
	@echo -e "FROM registry.opensuse.org/opensuse/leap:15.5\n"\
	"RUN zypper -n install make rpm-build\n" \
	"RUN zypper -n install -t pattern devel_C_C++" | \
	docker build --tag opensuse15.5 -f -  .  >> docker.log
.PHONY: docker_opensuse_tumbleweed
docker_opensuse_tumbleweed:
	@echo -e "\nopensuse_tumbleweed"
	@echo -e "FROM registry.opensuse.org/opensuse/tumbleweed:latest\n"\
	"RUN zypper -n install make rpm-build\n" \
	"RUN zypper -n install -t pattern devel_C_C++" | \
	docker build --tag opensuse_tumbleweed -f -  .  >> docker.log
.PHONY: docker_sle15
docker_sle15:
	@echo -e "\nsle15"
	@echo -e "FROM registry.suse.com/suse/sle15\n"\
	"RUN zypper -n install make rpm-build\n" \
	"RUN zypper -n install -t pattern devel_C_C++" | \
	docker build --tag sle15 -f -  .  >> docker.log

.PHONY: docker_clean
docker_clean:
	docker image rm sle15 || true
	docker image rm	opensuse_tumbleweed || true
	docker image rm	opensuse15.4 || true
	docker image rm	opensuse15.5 || true
	docker image rm rocky8.5 || true
	docker image rm rocky8 || true
	docker image rm	centos7 || true
	docker image rm	centos8 || true
	docker image rm	centos_stream || true
	docker image rm ubuntu_bionic || true
	docker image rm	ubuntu_focal || true
	docker image rm	ubuntu_jammy || true
	docker image rm	ubuntu_noble || true
	docker image rm	ubuntu_resolute || true
	docker image rm debian_buster || true
	docker image rm	debian_bullseye || true
	docker image rm	debian_bookworm || true
	docker image rm	debian_trixie || true

.PHONY: dockerised_deb_debian_buster
dockerised_deb_debian_buster: docker_debian_buster
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build debian_buster \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} debian_buster ${PKG_NAME} > $@.log

.PHONY: dockerised_deb_debian_bullseye
dockerised_deb_debian_bullseye: docker_debian_bullseye
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build debian_bullseye \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} debian_bullseye ${PKG_NAME} > $@.log

.PHONY: dockerised_deb_debian_bookworm
dockerised_deb_debian_bookworm: docker_debian_bookworm
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build debian_bookworm \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} debian_bookworm ${PKG_NAME} > $@.log

.PHONY: dockerised_deb_debian_trixie
dockerised_deb_debian_trixie: docker_debian_trixie
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build debian_trixie \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} debian_trixie ${PKG_NAME} > $@.log

.PHONY: dockerised_deb_ubuntu_bionic
dockerised_deb_ubuntu_bionic: docker_ubuntu_bionic
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build ubuntu_bionic \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} ubuntu_bionic ${PKG_NAME} > $@.log

.PHONY: dockerised_deb_ubuntu_focal
dockerised_deb_ubuntu_focal: docker_ubuntu_focal
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build ubuntu_focal \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} ubuntu_focal ${PKG_NAME} > $@.log

.PHONY: dockerised_rpm_centos7
dockerised_rpm_centos7: docker_centos7
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build centos7 \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} centos7 ${PKG_NAME} > $@.log

.PHONY: dockerised_rpm_centos8
dockerised_rpm_centos8: docker_centos8
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build centos8 \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} centos8 ${PKG_NAME} > $@.log

.PHONY: dockerised_rpm_centos_stream
dockerised_rpm_centos_stream: docker_centos_stream
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build centos_stream \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} centos_stream ${PKG_NAME} > $@.log

.PHONY: dockerised_rpm_rocky8.5
dockerised_rpm_rocky8.5: docker_rocky8.5
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build rocky8.5 \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} rocky8.5 ${PKG_NAME} > $@.log

.PHONY: dockerised_rpm_rocky8
dockerised_rpm_rocky8: docker_rocky8
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build rocky8 \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} rocky8 ${PKG_NAME} > $@.log

.PHONY: dockerised_rpm_opensuse15.4
dockerised_rpm_opensuse15.4: docker_opensuse15.4
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build opensuse15.4 \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} opensuse15.4 ${PKG_NAME} > $@.log

.PHONY: dockerised_rpm_opensuse15.5
dockerised_rpm_opensuse15.5: docker_opensuse15.5
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build opensuse15.5 \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} opensuse15.5 ${PKG_NAME} > $@.log

.PHONY: dockerised_rpm_opensuse_tumbleweed
dockerised_rpm_opensuse_tumbleweed: docker_opensuse_tumbleweed
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build opensuse_tumbleweed \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} opensuse_tumbleweed ${PKG_NAME} > $@.log

.PHONY: publish-to-repo
publish-to-repo:
	@rpmsign --addsign \
		../results/*/*rpm\
		|| {\
		@echo "Error signing packages:";\
		@echo "You may need a file $HOME/.rpmmacros containing:";\
		@echo "%_gpg_name ACDFB08FDC962044D87FF00B512839863D487A87";\
		};
	@scp ../results/centos7/* build@repo.data.kit.edu:/var/www/centos/centos7
	@scp ../results/centos8/* build@repo.data.kit.edu:/var/www/centos/centos8
	@scp ../results/centos_stream/* build@repo.data.kit.edu:/var/www/centos/centos-stream
	@scp ../results/rocky8.5/* build@repo.data.kit.edu:/var/www/rocky/rocky8.5
	@scp ../results/rocky8/* build@repo.data.kit.edu:/var/www/rocky/rocky8
	@scp ../results/debian_buster/* build@repo.data.kit.edu:/var/www/debian/buster
	@scp ../results/debian_bullseye/* build@repo.data.kit.edu:/var/www/debian/bullseye
	@scp ../results/debian_bookworm/* build@repo.data.kit.edu:/var/www/debian/bookworm
	@scp ../results/debian_trixie/* build@repo.data.kit.edu:/var/www/debian/bookworm
	@scp ../results/ubuntu_bionic/* build@repo.data.kit.edu:/var/www/ubuntu/bionic 
	@scp ../results/ubuntu_focal/* build@repo.data.kit.edu:/var/www/ubuntu/focal
	@scp ../results/ubuntu_jammy/* build@repo.data.kit.edu:/var/www/ubuntu/focal
	@scp ../results/ubuntu_noble/* build@repo.data.kit.edu:/var/www/ubuntu/focal
	@scp ../results/ubuntu_resolute/* build@repo.data.kit.edu:/var/www/ubuntu/focal
	@scp ../results/opensuse15.4/* build@repo.data.kit.edu:/var/www/suse/opensuse-leap-15.4
	@scp ../results/opensuse15.5/* build@repo.data.kit.edu:/var/www/suse/opensuse-leap-15.5
	@scp ../results/opensuse_tumbleweed/* build@repo.data.kit.edu:/var/www/suse/opensuse-tumbleweed
	#@scp ../results/sle15/* build@repo.data.kit.edu:/var/www/suse/sle15

# Debian Packaging

.PHONY: preparedeb
preparedeb: distclean
	@quilt pop -a || true
	@debian/rules clean
	( cd ..; tar czf ${PKG_NAME}_${DEBIAN_VERSION}.orig.tar.gz --exclude-vcs --exclude=debian --exclude=.pc ${PKG_NAME_UNDERSCORES})

.PHONY: debsource
debsource: preparedeb
	dpkg-source -b .

.PHONY: deb
deb: cleanapi create_obj_dir_structure preparedeb
	dpkg-buildpackage -i -b -uc -us
	@echo "Success: DEBs are in parent directory"

# RPM Packaging

.PHONY: rpmsource
rpmsource: virtualenv
	(cd ..; tar czf $(SRC_TAR) --exclude-from=$(PKG_NAME_UNDERSCORES)/.gitignore --exclude-vcs --exclude-caches-all \
		$(PKG_NAME_UNDERSCORES) --transform='s^${PKG_NAME_UNDERSCORES}^${PKG_NAME}-$(RPM_VERSION)^')
	mkdir -p rpm/rpmbuild/SOURCES
	mv ../$(SRC_TAR) rpm/rpmbuild/SOURCES/
	cp rpm/*.patch rpm/rpmbuild/SOURCES/

.PHONY: virtualenv # called from specfile
virtualenv:
	@echo "Building virtualenv with: $(PYTHON) ($$($(PYTHON) --version 2>&1))"
	$(PYTHON) -m venv venv
	venv/bin/python -m pip install --upgrade pip
	venv/bin/python -m pip install -I -r requirements.txt build
	venv/bin/python -m pip freeze > venv/all_versions.txt

.PHONY: rpms
rpms: srpm rpm 

.PHONY: rpm
rpm: rpmsource
	echo ${PATH}
	pip --version
	rpmbuild --define "_basedir ${PWD}" --define "_topdir ${PWD}/rpm/rpmbuild" --define "_build_id_links none" -bb  rpm/${PKG_NAME}.spec

.PHONY: srpm
srpm: rpmsource
	rpmbuild --define "_basedir ${PWD}" --define "_topdir ${PWD}/rpm/rpmbuild" -bs  rpm/${PKG_NAME}.spec

.PHONY: install # called from specfile
install:
	install -D -d -m 755 ${DESTDIR}/usr/lib/${PKG_NAME}
	cp -af venv/* ${DESTDIR}/usr/lib/${PKG_NAME}
	# Invoke the copied venv's interpreter directly: its console-script
	# shebangs still point at the build path until fix-venv-paths.sh runs.
	${DESTDIR}/usr/lib/${PKG_NAME}/bin/python -m pip install . --prefix ${DESTDIR}/usr/lib/${PKG_NAME}
	@test -e ${DESTDIR}/usr/lib/motley-cue/.gitignore && rm ${DESTDIR}/usr/lib/motley-cue/.gitignore || true
