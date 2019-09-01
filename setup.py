from setuptools import setup

setup(name='zlx',
      version='0.0',
      description='Zalmoxis - module for text and binary manipulation',
      url='https://gitlab.com/icostin/zlx-py',
      author='Costin Ionescu',
      author_email='costin.ionescu@gmail.com',
      license='MIT',
      packages=['zlx'],
      zip_safe=False,
      entry_points = {
          'console_scripts': ['zlx=zlx.cmd_line:entry'],
      })

