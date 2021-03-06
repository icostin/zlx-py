.PHONY: all clean test test-py2 test-py3 dist

PREFIX_DIR=$(HOME)/.local

all: test-py3 test-py2

clean:
	-rm -rf zlx/*.pyc zlx/__pycache__ _temp build dist zlx.egg-info

test:
	PYTHONPATH=. python test/test.py

test-py2: _temp/hello32.exe _temp/hello64.exe | _temp
	PYTHONPATH=. python2 zlx.py test
	PYTHONPATH=. python2 zlx.py map-pe _temp/hello32.exe -o _temp/hello32.py2.bin
	PYTHONPATH=. python2 zlx.py map-pe _temp/hello64.exe -o _temp/hello64.py2.bin

test-py3: _temp/hello32.exe _temp/hello64.exe | _temp
	PYTHONPATH=. python3 zlx.py test
	PYTHONPATH=. python3 zlx.py map-pe _temp/hello32.exe -o _temp/hello32.py3.bin
	PYTHONPATH=. python3 zlx.py map-pe _temp/hello64.exe -o _temp/hello64.py3.bin

_temp/hello32.exe: test/hello.c | _temp
	i686-w64-mingw32-gcc -o $@ $<

_temp/hello64.exe: test/hello.c | _temp
	x86_64-w64-mingw32-gcc -o $@ $<

_temp:
	mkdir -p $@

dev-install:
	pip3 install -e .

install-manual:
	install zlx.sh $(PREFIX_DIR)/bin/zlx
	mkdir -p $(PREFIX_DIR)/lib/zlx-py/zlx
	cp -f zlx.py $(PREFIX_DIR)/lib/zlx-py
	cp -rf zlx/*.py $(PREFIX_DIR)/lib/zlx-py/zlx

uninstall-manual:
	rm -rf $(PREFIX_DIR)/bin/zlx $(PREFIX_DIR)/lib/zlx-py

inc-build:
	zlx inc-build zlx/__init__.py

dist:
	python3 setup.py sdist bdist_wheel

upload:
	twine upload dist/*
