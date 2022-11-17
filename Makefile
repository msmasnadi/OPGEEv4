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
	pip install -e .

EMPTY :=
SPACE := $(EMPTY) $(EMPTY)
RQMTS := $(shell cat requirements.in)
MODS  := $(subst $(SPACE),|,$(RQMTS))
EXPR  := $(shell printf "^(%s)=\n" '$(MODS)')

RTD_REQS = rtd.requirements.txt
TRAVIS_REQS = requirements.txt

clean-reqs:
	rm $(RTD_REQS) $(TRAVIS_REQS)

rtd-reqs $(RTD_REQS): requirements.in
	python -V|sed -e 's/Python /python==/' > $(RTD_REQS)
	pip freeze | egrep '$(EXPR)' >> $(RTD_REQS)

# "pip freeze" erroneously reports pytest==0.0.0
travis-reqs $(TRAVIS_REQS): requirements.in
	./update-reqs.py

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

install-opgee:
	bash -l -c 'conda activate opgee && pip install -e .'

rebuild-opgee: remove-opgee create-opgee install-opgee

NUITKA_EXE    = opgee.exe
NUITKA_OUTDIR = /tmp/opgee-nuitka
NUITKA_LOG    = /tmp/opgee-nuitka.txt

$(NUITKA_EXE):
	python -m nuitka opgee/main.py -o $@ \
		--output-dir=$(NUITKA_OUTDIR) \
		--include-package-data=opgee \
		--onefile \
		--plugin-enable=numpy \
		--plugin-enable=pylint-warnings \
		--warn-unusual-code \
		--warn-implicit-exceptions \
		--verbose --verbose-output=$(NUITKA_LOG)
#		--standalone
