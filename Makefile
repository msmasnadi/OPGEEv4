# From http://peterdowns.com/posts/first-time-with-pypi.html
# To register a package on PyPiTest:
# python setup.py register -r pypitest
#
# Then to upload the actual package:
# python setup.py sdist upload -r pypitest
#
# Do the same with pypi instead of pypitest to go live
.ONESHELL:
SHELL=/bin/bash
CONDA_ENV = opgee
CONDA_ACTIVATE = source $$(conda info --base)/etc/profile.d/conda.sh; conda activate; conda activate

LOCK=opgee.conda.lock
ifeq ($(OS),Windows_NT)
    CONDA_INIT_CMD = call "$(shell where conda | grep Scripts\\conda.exe | sed 's/conda.exe/activate.bat/')"
    CONDA_PATH_CHECK = where conda
    CONDA_INIT_IN_SUBSHELL = call activate.bat
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Linux)
        CONDA_ROOT = ~/anaconda3
        CONDA_INIT_CMD = source $(CONDA_ROOT)/bin/activate
        CONDA_PATH_CHECK = which conda
    else
        UNAME_P := $(shell uname -p)
        ifeq ($(UNAME_P),arm)
            CONDA_ROOT = /opt/homebrew/anaconda3
            CONDA_INIT_CMD = source $(CONDA_ROOT)/bin/activate
            CONDA_PATH_CHECK = which conda
        else
            CONDA_ROOT = ~/anaconda3
            CONDA_INIT_CMD = source $(CONDA_ROOT)/bin/activate
            CONDA_PATH_CHECK = which conda
        endif
    endif
    CONDA_INIT_IN_SUBSHELL = source $(CONDA_ROOT)/bin/activate
endif

check-conda:
	@$(CONDA_PATH_CHECK) >/dev/null 2>&1 || \
	(echo "Conda not found. Initializing conda..." && \
	$(CONDA_INIT_CMD))
	
act:
	$(CONDA_ACTIVATE)
a: act
	# py=$$(which python3)
	# @echo "before $$py"
	# $(CONDA_ACTIVATE) base
	py2=$$(which python)
	echo "after $$py2"
	
t: 
	py=$$(which python3)
	echo "after $$py"
	
list:
	@$(CONDA_ACTIVATE) ./foo; conda list

dc:
	$(conda deactivate)

check-active-env: check-conda
	@bash -c '$(CONDA_INIT_IN_SUBSHELL) && \
	active_env=$$(conda info --envs | grep "*" | cut -d" " -f1) && \
	echo "Current environment: $$active_env" && \
	if [ "$$active_env" = "$(CONDA_ENV)" ]; then \
		echo "Deactivating $(CONDA_ENV) environment..." && \
		conda deactivate; \
	else \
		echo "Environment $(CONDA_ENV) is not active"; \
	fi'

remove-opgee: check-conda check-active-env
	@echo "Removing $(CONDA_ENV) environment..."
	@conda env remove -n $(CONDA_ENV)
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
YML_FILE=py3-opgee.yml


#INPUT_YML=py3-opgee-macos.yml
#
#test-yml: $(TEST_YML)
#
## drops all commment lines
#$(TEST_YML) : $(INPUT_YML)
#	egrep -v '^#' $(INPUT_YML) > $(TEST_YML)

# remove-opgee:
# 	conda env remove -n opgee

create-opgee: $(YML_FILE)
	conda env create -f $(YML_FILE)

install-opgee:
	bash -l -c 'conda activate opgee && pip install -e .'

rebuild-opgee: remove-opgee create-opgee travis-reqs install-opgee

# Generate a detailed package list to cache for validation of
# environment on CI platform (currently github actions)
env-pkg-list:
	conda list --export > opgee.pkg_list.txt

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
