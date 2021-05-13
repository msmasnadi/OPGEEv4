# From http://peterdowns.com/posts/first-time-with-pypi.html
# To register a package on PyPiTest:
# python setup.py register -r pypitest
#
# Then to upload the actual package:
# python setup.py sdist upload -r pypitest
#
# Do the same with pypi instead of pypitest to go live

all: clean html sdist wheel

version = `./version.sh`

test-upload: # sdist
	twine upload dist/opgee-$(version).tar.gz -r testpypi

upload: pypi-upload

pypi-upload: sdist
	twine upload dist/opgee-$(version).tar.gz

clean-html:
	make -C docs clean

html:
	make -C docs html

pdf:
	make -C docs latexpdf

clean-setup:
	python setup.py clean

sdist:
	python setup.py sdist

wheel:
	python setup.py bdist_wheel

clean: clean-html clean-setup clean-requirements

dev:
	pip install -e

EMPTY :=
SPACE := $(EMPTY) $(EMPTY)
RQMTS := $(shell cat requirements.in)
MODS  := $(subst $(SPACE),|,$(RQMTS))
EXPR  := $(shell printf "^(%s)=\n" '$(MODS)')

RTD_REQS = rtd.requirements.txt
TRAVIS_REQS = requirements.txt

clean-requirements:
	rm $(RTD_REQS) $(TRAVIS_REQS)

rtd-reqs $(RTD_REQS): requirements.in
	python -V|sed -e 's/Python /python==/' > $(RTD_REQS)
	pip freeze | egrep '$(EXPR)' >> $(RTD_REQS)

travis-reqs $(TRAVIS_REQS): requirements.in
	python -V|sed -e 's/Python /python>=/' > $(TRAVIS_REQS)
	pip freeze | egrep '$(EXPR)' >> $(TRAVIS_REQS)
