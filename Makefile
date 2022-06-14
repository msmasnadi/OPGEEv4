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

# "pip freeze" erroneously reports pytest==0.0.0
travis-reqs $(TRAVIS_REQS): requirements.in
	echo "colour"       > $(TRAVIS_REQS)
	echo "dash"        >> $(TRAVIS_REQS)
	echo "numpy"       >> $(TRAVIS_REQS)
	echo "pandas"      >> $(TRAVIS_REQS)
	echo "pint"        >> $(TRAVIS_REQS)
	echo "pint-pandas" >> $(TRAVIS_REQS)
	echo "pytest"      >> $(TRAVIS_REQS)
	echo "scipy"       >> $(TRAVIS_REQS)
	echo "pytest-cov"  >> $(TRAVIS_REQS)
	echo "codecov"     >> $(TRAVIS_REQS)
	pip freeze | egrep -v '^(numpy|pandas|pint|pytest|scipy)' | egrep '$(EXPR)' >> $(TRAVIS_REQS)

test:
	@echo "pip freeze | egrep -v '^(numpy|pandas|pint|pytest|scipy)' | egrep '$(EXPR)' >> $(TRAVIS_REQS)"

#
# Virtual environment / package dependency support
#
TEST_YML=py3-opgee-macos.yml

#INPUT_YML=py3-opgee-macos.yml
#
#test-yml: $(TEST_YML)
#
## drops all commment lines
#$(TEST_YML) : $(INPUT_YML)
#	egrep -v '^#' $(INPUT_YML) > $(TEST_YML)

remove-opgee:
	conda env remove -n opgee

create-opgee: $(TEST_YML)
	conda env create -f $(TEST_YML)
	conda activate opgee
	python setup.py develop

rebuild-opgee: remove-opgee create-opgee

NUITKA_EXE    = opgee.exe
NUITKA_OUTDIR = /tmp/opgee-nuitka
NUITKA_LOG    = /tmp/opgee-nuitka.txt

$(NUITKA_EXE):
	python -m nuitka opgee/main.py -o $@ \
		--output-dir=$(NUITKA_OUTDIR) \
		--include-package-data=opgee \
		--onefile \
		--enable-plugin=numpy \
		--warn-unusual-code \
		--verbose --verbose-output=$(NUITKA_LOG)
#		--standalone \
