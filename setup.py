from setuptools import setup
import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import zlx

ZLX_DESC = '''
# Zalmoxis

Zalmoxis is a python module for text and binary manipulation.
zlx.io submodule offers convenient wrappers for streams and byte-array
that encode/decode items.

'''

setup(name='zlx',
      version = zlx.VER_STR,
      description = 'Zalmoxis - module for text and binary manipulation',
      long_description = ZLX_DESC,
      long_description_content_type = "text/markdown",
      url = 'https://gitlab.com/icostin/zlx-py',
      author = 'Costin Ionescu',
      author_email = 'costin.ionescu@gmail.com',
      license = 'MIT',
      packages = ['zlx'],
      zip_safe = False,
      entry_points = {
          'console_scripts': ['zlx=zlx.cmd_line:entry'],
      },
      classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
      )

