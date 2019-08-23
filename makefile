.PHONY: all clean test test-py2 test-py3

all: test-py2 test-py3

clean:
	-rm -rf zlx/*.pyc zlx/__pycache__ _temp

test:
	PYTHONPATH=. python test/test.py

test-py2: _temp/hello32.exe _temp/hello64.exe | _temp
	PYTHONPATH=. python2 test/test.py
	PYTHONPATH=. python2 test/test.py map-pe _temp/hello32.exe _temp/hello32.py2.bin
	PYTHONPATH=. python2 test/test.py map-pe _temp/hello64.exe _temp/hello64.py2.bin

test-py3: _temp/hello32.exe _temp/hello64.exe | _temp
	PYTHONPATH=. python3 test/test.py
	PYTHONPATH=. python3 test/test.py map-pe _temp/hello32.exe _temp/hello32.py3.bin
	PYTHONPATH=. python3 test/test.py map-pe _temp/hello64.exe _temp/hello64.py3.bin

_temp/hello32.exe: test/hello.c | _temp
	i686-w64-mingw32-gcc -o $@ $<

_temp/hello64.exe: test/hello.c | _temp
	x86_64-w64-mingw32-gcc -o $@ $<

_temp:
	mkdir -p $@