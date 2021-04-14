PKG_NAME  = motley-cue
PKG_NAME_UNDERSCORES  = motley_cue
#VERSION := $(shell ./setup.py --version)
VERSION := $(shell git tag -l --sort=committerdate | tail -n 1 | sed s/v//)
#VERSION := 0.0.4

BASEDIR = $(PWD)
BASENAME := $(notdir $(PWD))
DOCKER_BASE=`dirname ${PWD}`
PACKAGE=`basename ${PWD}`
SRC_TAR:=$(PKG_NAME).tar


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
dockerised_all_packages: dockerised_deb_debian_buster dockerised_deb_debian_bullseye dockerised_deb_ubuntu_bionic dockerised_deb_ubuntu_focal dockerised_rpm_centos8

docker_images: docker_centos8 docker_debian_bullseye docker_debian_buster docker_ubuntu_bionic docker_ubuntu_focal
docker_debian_buster:
	echo "\ndebian_buster"
	@echo -e "FROM debian:buster\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv dh-virtualenv python3-venv devscripts git "\
    	"python3 python3-dev python3-pip python3-setuptools "| \
	docker build --tag debian_buster -f - .
docker_debian_bullseye:
	echo "\ndebian_bullseye"
	@echo -e "FROM debian:bullseye\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv dh-virtualenv python3-venv devscripts git "\
		"python3 python3-dev python3-pip python3-setuptools "| \
	docker build --tag debian_bullseye -f - .
docker_ubuntu_bionic:
	echo "\nubuntu_bionic"
	@echo -e "FROM ubuntu:bionic\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv dh-virtualenv python3-venv devscripts git "\
		"python3 python3-dev python3-pip python3-setuptools "| \
	docker build --tag ubuntu_bionic -f - .
docker_ubuntu_focal:
	echo "\nubuntu_focal"
	@echo -e "FROM ubuntu:focal\n"\
	"ENV DEBIAN_FRONTEND=noninteractive\n"\
	"ENV  TZ=Europe/Berlin\n"\
	"RUN apt-get update && "\
		"apt-get -y upgrade && "\
		"apt-get -y install build-essential dh-make quilt "\
		"python3-virtualenv python3-venv devscripts git "\
		"python3 python3-dev python3-pip python3-setuptools "| \
	docker build --tag ubuntu_focal -f - .
docker_centos8:
	echo "\ncentos8"
	@echo -e "FROM centos:8\n"\
	"RUN yum install -y make rpm-build\n" \
	"RUN dnf -y group install \"Development Tools\"\n" | \
	docker build --tag centos8 -f -  .

.PHONY: dockerised_deb_debian_buster
dockerised_deb_debian_buster: docker_debian_buster
	@docker run -it --rm -v ${DOCKER_BASE}:/home/build debian_buster /home/build/${PACKAGE}/build.sh ${PACKAGE} debian_buster ${PKG_NAME}

.PHONY: dockerised_deb_debian_bullseye
dockerised_deb_debian_bullseye: docker_debian_bullseye
	@docker run -it --rm -v ${DOCKER_BASE}:/home/build debian_bullseye \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} debian_bullseye ${PKG_NAME}

.PHONY: dockerised_deb_ubuntu_bionic
dockerised_deb_ubuntu_bionic: docker_ubuntu_bionic
	@docker run -it --rm -v ${DOCKER_BASE}:/home/build ubuntu_bionic \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} ubuntu_bionic ${PKG_NAME}

.PHONY: dockerised_deb_ubuntu_focal
dockerised_deb_ubuntu_focal: docker_ubuntu_focal
	@docker run -it --rm -v ${DOCKER_BASE}:/home/build ubuntu_focal \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} ubuntu_focal ${PKG_NAME}

.PHONY: dockerised_rpm_centos8
dockerised_rpm_centos8: docker_centos8
	@docker run -it --rm -v ${DOCKER_BASE}:/home/build centos8 \
		/home/build/${PACKAGE}/build.sh ${PACKAGE} centos8 ${PKG_NAME}

.PHONE: publish-to-repo
publish-to-repo:
	@scp ../results/centos8/* build@repo.data.kit.edu:/var/www/centos/centos8
	@scp ../results/debian_buster/* build@repo.data.kit.edu:/var/www/debian/buster
	@scp ../results/debian_bullseye/* build@repo.data.kit.edu:/var/www/debian/bullseye
	@scp ../results/ubuntu_bionic/* build@repo.data.kit.edu:/var/www/ubuntu/bionic 
	@scp ../results/ubuntu_focal/* build@repo.data.kit.edu:/var/www/ubuntu/focal

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
srctar:
	(cd ..; tar cf $(BASENAME)/$(SRC_TAR) $(PKG_NAME_UNDERSCORES) --transform='s^${PKG_NAME_UNDERSCORES}^${PKG_NAME}-$(VERSION)^')
	mkdir -p rpm/rpmbuild/SOURCES
	mv $(SRC_TAR) rpm/rpmbuild/SOURCES/

.PHONY: virtualenv # called from specfile
virtualenv:
	virtualenv-3 ${DESTDIR}/usr/lib/${PKG_NAME}
	( \
		source ${DESTDIR}/usr/lib/${PKG_NAME}/bin/activate; \
		echo "PATH"; \
		echo ${PATH}; \
		pip --version; \
		pip install -r requirements.txt; \
	)

.PHONY: rpm
rpm: srctar
	echo ${PATH}
	pip --version
	QA_SKIP_BUILD_ROOT=1 rpmbuild --define "_topdir ${PWD}/rpm/rpmbuild" -bb  rpm/${PKG_NAME}.spec

.PHONY: install # called from specfile
install: virtualenv
	( \
		source ${DESTDIR}/usr/lib/${PKG_NAME}/bin/activate; \
		python3 ./setup.py install --prefix ${DESTDIR}; \
	)
	rm -rf ${DESTDIR}/usr/lib/.build-id
