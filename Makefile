PKG_NAME  = motley-cue
PKG_NAME_UNDERSCORES  = motley_cue

DEBIAN_VERSION := $(shell head debian/changelog  -n 1 | cut -d \( -f 2 | cut -d \) -f 1 | cut -d \- -f 1)
VERSION := $(DEBIAN_VERSION)

# Parallel builds:
MAKEFLAGS += -j5

BASEDIR = $(PWD)
BASENAME := $(notdir $(PWD))
DOCKER_BASE=`dirname ${PWD}`
PACKAGE=`basename ${PWD}`
SRC_TAR:=$(PKG_NAME).tar.gz

SHELL:=bash
#VIRTUALENV:=$(shell virtualenv --version ; shell if [ $? == 0 ]; then echo "virtualenv"; else echo "virtualenv-3"; fi)
HAS_VENV:=$(shell virtualenv    --version >/dev/null 2>&1 && echo "yes" || echo "")
HAS_VENV3:=$(shell virtualenv-3 --version >/dev/null 2>&1 && echo "yes" || echo "")
ifeq ($(HAS_VENV),yes)
	VIRTUALENV:=virtualenv
endif
ifeq ($(HAS_VENV3),yes)
	VIRTUALENV:=virtualenv-3
endif

info:
	@echo "############################################################"
	@echo "DESTDIR: ${DESTDIR}"
	@echo "BASEDIR: ${BASEDIR}"
	@echo "VIRTUALENV: ${VIRTUALENV}"
	#env
	@echo "############################################################"

### Actual targets
default: sdist bdist_wheel

sdist:
	python3 ./setup.py sdist
bdist_wheel:
	python3 ./setup.py bdist_wheel

dist: sdist bdist_wheel

clean: cleandist
	rm -rf build 
	rm -rf doc/build
	rm -rf *.egg-info
	rm -rf .eggs

distclean: clean
	rm -rf .tox
	rm -rf .pytest_cache
	find -type d -name __pycache__ | xargs rm -rf 

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
	dockerised_rpm_centos8\

.PHONY: dockerised_most_packages
dockerised_most_packages: dockerised_deb_debian_buster\
	dockerised_deb_debian_bullseye\
	dockerised_deb_debian_bookworm\
	dockerised_rpm_centos7\
	dockerised_rpm_centos8\
	dockerised_rpm_opensuse_tumbleweed\

.PHONY: dockerised_all_packages
dockerised_all_packages: dockerised_deb_debian_buster\
	dockerised_deb_debian_bullseye\
	dockerised_deb_debian_bookworm\
	dockerised_deb_ubuntu_bionic\
	dockerised_deb_ubuntu_focal\
	dockerised_rpm_centos7\
	dockerised_rpm_centos8\
	dockerised_rpm_opensuse15.2\
	dockerised_rpm_opensuse15.3\
	dockerised_rpm_opensuse_tumbleweed

.PHONY: docker_images
docker_images: docker_centos8\
	docker_centos7\
	docker_debian_bullseye\
	docker_debian_buster\
	docker_debian_bookworm\
	docker_ubuntu_bionic\
	docker_ubuntu_focal\
	docker_opensuse15.2\
	docker_opensuse15.3\
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
.PHONY: docker_ubuntu_bionic
docker_ubuntu_bionic:
	@echo -e "\nubuntu_bionic"
	@echo -e "FROM ubuntu:bionic\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv dh-virtualenv python3-venv devscripts git "\
		"python3 python3-dev python3-pip python3-setuptools "| \
	docker build --tag ubuntu_bionic -f - .  >> docker.log
.PHONY: docker_ubuntu_focal
docker_ubuntu_focal:
	@echo -e "\nubuntu_focal"
	@echo -e "FROM ubuntu:focal\n"\
	"ENV DEBIAN_FRONTEND=noninteractive\n"\
	"ENV  TZ=Europe/Berlin\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv python3-venv devscripts git "\
		"python3 python3-dev python3-pip python3-setuptools "| \
	docker build --tag ubuntu_focal -f - .  >> docker.log
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
	"RUN yum install -y make rpm-build\n" \
	"RUN dnf -y group install \"Development Tools\"\n" | \
	docker build --tag centos8 -f -  .  >> docker.log
.PHONY: docker_opensuse15.2
docker_opensuse15.2:
	@echo -e "\nopensuse-15.2"
	@echo -e "FROM registry.opensuse.org/opensuse/leap:15.2\n"\
	"RUN zypper -n install make rpm-build\n" \
	"RUN zypper -n install -t pattern devel_C_C++" | \
	docker build --tag opensuse15.2 -f -  .  >> docker.log
.PHONY: docker_opensuse15.3
docker_opensuse15.3:
	@echo -e "\nopensuse-15.3"
	@echo -e "FROM registry.opensuse.org/opensuse/leap:15.3\n"\
	"RUN zypper -n install make rpm-build\n" \
	"RUN zypper -n install -t pattern devel_C_C++" | \
	docker build --tag opensuse15.3 -f -  .  >> docker.log
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
	docker image rm opensuse15.2 || true
	docker image rm	opensuse15.3 || true
	docker image rm centos8 || true
	docker image rm	centos7 || true
	docker image rm ubuntu_bionic || true
	docker image rm	ubuntu_focal || true
	docker image rm debian_buster || true
	docker image rm	debian_bullseye || true
	docker image rm	debian_bookworm || true

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

.PHONY: dockerised_rpm_opensuse15.2
dockerised_rpm_opensuse15.2: docker_opensuse15.2
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build opensuse15.2 \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} opensuse15.2 ${PKG_NAME} > $@.log

.PHONY: dockerised_rpm_opensuse15.3
dockerised_rpm_opensuse15.3: docker_opensuse15.3
	@echo "Writing build log to $@.log"
	@docker run --tty --rm -v ${DOCKER_BASE}:/home/build opensuse15.3 \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} opensuse15.3 ${PKG_NAME} > $@.log

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
	@scp ../results/debian_buster/* build@repo.data.kit.edu:/var/www/debian/buster
	@scp ../results/debian_bullseye/* build@repo.data.kit.edu:/var/www/debian/bullseye
	@scp ../results/debian_bookworm/* build@repo.data.kit.edu:/var/www/debian/bookworm
	@scp ../results/ubuntu_bionic/* build@repo.data.kit.edu:/var/www/ubuntu/bionic 
	@scp ../results/ubuntu_focal/* build@repo.data.kit.edu:/var/www/ubuntu/focal
	@scp ../results/opensuse15.2/* build@repo.data.kit.edu:/var/www/suse/opensuse-leap-15.2
	@scp ../results/opensuse15.3/* build@repo.data.kit.edu:/var/www/suse/opensuse-leap-15.3
	@scp ../results/opensuse_tumbleweed/* build@repo.data.kit.edu:/var/www/suse/opensuse-tumbleweed
	#@scp ../results/sle15/* build@repo.data.kit.edu:/var/www/suse/sle15

# Debian Packaging

.PHONY: preparedeb
preparedeb: clean
	@quilt pop -a || true
	@debian/rules clean
	( cd ..; tar czf ${PKG_NAME}_${VERSION}.orig.tar.gz --exclude-vcs --exclude=debian --exclude=.pc ${PKG_NAME_UNDERSCORES})

.PHONY: debsource
debsource: distclean preparedeb
	dpkg-source -b .

.PHONY: deb
deb: cleanapi create_obj_dir_structure preparedeb
	dpkg-buildpackage -i -b -uc -us
	@echo "Success: DEBs are in parent directory"

# RPM Packaging

.PHONY: srctar
srctar: virtualenv
	(cd ..; tar czf $(SRC_TAR) --exclude-vcs --exclude=.pc $(PKG_NAME_UNDERSCORES) --transform='s^${PKG_NAME_UNDERSCORES}^${PKG_NAME}-$(VERSION)^')
	mkdir -p rpm/rpmbuild/SOURCES
	mv ../$(SRC_TAR) rpm/rpmbuild/SOURCES/
	cp rpm/logfiles.patch rpm/rpmbuild/SOURCES/

.PHONY: virtualenv # called from specfile
virtualenv:
	${VIRTUALENV} venv
	( \
		source venv/bin/activate; \
		echo "PATH"; \
		echo ${PATH}; \
		pip --version; \
		pip install -I -r requirements.txt; \
		pip freeze > venv/all_versions.txt; \
	)

.PHONY: rpms
rpms: srpm rpm 

.PHONY: rpm
rpm: srctar
	echo ${PATH}
	pip --version
	rpmbuild --define "_topdir ${PWD}/rpm/rpmbuild" --define "_build_id_links none" -bb  rpm/${PKG_NAME}.spec

.PHONY: srpm
srpm: srctar
	rpmbuild --define "_topdir ${PWD}/rpm/rpmbuild" -bs  rpm/${PKG_NAME}.spec

.PHONY: install # called from specfile
install:
	install -D -d -m 755 ${DESTDIR}/usr/lib/${PKG_NAME}
	cp -af venv/* ${DESTDIR}/usr/lib/${PKG_NAME}
	( \
		source ${DESTDIR}/usr/lib/${PKG_NAME}/bin/activate; \
		python3 ./setup.py install --prefix ${DESTDIR}/usr/lib/${PKG_NAME}; \
	)
	@test -e ${DESTDIR}/usr/lib/motley-cue/.gitignore && rm ${DESTDIR}/usr/lib/motley-cue/.gitignore || true
