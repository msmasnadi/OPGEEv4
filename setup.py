from opgee.version import VERSION
from setuptools import setup

requirements = [
    'colour>=0.1.5',    # used with dash app
    'dash>=1.19.0',
    'ipython>=7.18.0',
    'Jinja2>=3.0',      # required by flask, via dash
    'lxml>=4.8.0',
    'networkx>=2.5.0',

    'numpy>=1.21.0',
    'pandas>=1.4.0',

    'pint>=0.19',
    'pint-pandas>=0.2',
    'pydot>=1.4.0',
    'pytest>=6.1.0',
    'sphinx>=3.2.0'
    'sphinx-argparse>=0.2.0',
    'sphinx-rtd-theme>=0.4.0',
    'thermosteam==0.28.5',
]

long_description = '''
opgee
=======

The ``opgee`` package provides ...

Full documentation and a tutorial are available at
https://opgee.readthedocs.io.

Core functionality
------------------

* TBD

Who do I talk to?
------------------

* TBD
'''

setup(
    name='opgee',
    version=VERSION,
    description='Python 3 package implementing life cycle analysis of oil fields',
    platforms=['Windows', 'MacOS', 'Linux'],

    packages=['opgee'],
    entry_points={'console_scripts': ['opg = opgee.tool:main']},
    install_requires=requirements,
    include_package_data = True,

    # extras_require=extras_requirements,

    url='https://github.com/rjplevin/opgee',
    download_url='https://github.com/arbrandt/OPGEEv4.git',
    license='MIT License',
    author='Richard Plevin',
    author_email='rich@plevin.com',

    classifiers=[
          # 'Development Status :: 5 - Production/Stable',
          'Development Status :: 2 - Pre-Alpha',
          'License :: OSI Approved :: MIT License',
          'Intended Audience :: Science/Research',
          ],

    zip_safe=True,
)
