from opgee.version import VERSION
from setuptools import setup

requirements = [
    #'colour>=0.1.5',    # used with dash app
    'dash>=2.3.1',
    'dash-cytoscape>=0.3.0',
    'ipython',
    # 'Jinja2',      # required by flask, via dash
    'lxml',
    'networkx',
    'numba',
    'numpy',
    'pandas',
    'pint',
    'pint-pandas',
    'pydot',
    'pytest',
    'sphinx>=4.3.0',
    'sphinx-argparse>=0.2.5',
    'sphinx-rtd-theme>=0.5.1',
    'thermosteam',
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
