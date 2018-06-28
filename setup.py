import os
from setuptools import setup, find_packages

req_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "requirements.txt")
with open(req_path) as f:
    requires = f.read().splitlines()

setup(name='planet-util',
      version='0.0.1',
      description='High level utils for working with planet data',
      classifiers=[],
      keywords='',
      author='Pramukta Kumar',
      author_email='pramukta.kumar@gmail.com',
      url='https://github.com/pramukta/planet-util',
      license='MIT',
      entry_points = {
          'console_scripts': ['planet-util=planet_util.cli:cli']
      },
      packages=find_packages(exclude=['docs','tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=requires
      )
