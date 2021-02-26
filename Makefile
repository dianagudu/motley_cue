PKG_NAME  = motley-cue
PKG_NAME_UNDERSCORES  = motley_cue
#VERSION := $(shell ./setup.py --version)
VERSION := $(shell git tag -l  | tail -n 1 | sed s/v//)
#VERSION := 0.0.4

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

# Packaging
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
