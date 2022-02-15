PERFHOME = /p/dpg/arch/perfhome
PYTHON   = $(PERFHOME)/python/miniconda

all: test

isort:
	@echo "[ isort ]"
	$(PYTHON)/bin/isort --skip reports

isort-check:
	@echo "[ isort ]"
	@$(PYTHON)/bin/isort --check-only --skip reports || ( echo "Run 'make isort' to fix imports order"; exit 1 )

pylint:
	@echo "[ pylint ]"
	@$(PYTHON)/bin/pylint *

flake8:
	@echo "[ flake8 ]"
	@$(PYTHON)/bin/flake8 --max-line-length=120 * --exclude reports,README.md,Makefile,setup.csh

lint: isort-check flake8


test:
	@echo "[ Regression ]"
	@run_regression.py

install:
	@if [ "$(VERSION)" = "" ]; then \
                echo "Tag repository, push tags and run: make install VERSION=M.m.r"; \
                exit 1; \
        fi
	$(PERFHOME)/bin/install_from_gitlab \
                --repository speed-public-pkgs/speedsim --tool speedsim --version $(VERSION) \
                --shallow 1 --recursive \
                --extra-cmd 'rm -rf $(PERFHOME)/speedsim/latest/test $(PERFHOME)/speedsim/latest/asap/test $(PERFHOME)/speedsim/latest/pnets/test $(PERFHOME)/speedsim/latest/doc'

clean:
	git clean -xfd

.PHONY: all clean test install
