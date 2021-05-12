from opgee.version import VERSION

# Build the full version with MCS on when running on ReadTheDocs.
# In normal mode, MCS is an optional install.
# import os
# import platform
#
# if platform.system() != 'Windows':
#     # Unfortunately, this stalled on Windows when I tested it...
#     import ez_setup
#     ez_setup.use_setuptools(version='36.7.2')


from setuptools import setup

requirements = [
    'ipython>=7.2',
    'future>=0.18.0',
    'lxml>=4.6.0',
    'networkx>=2.5.0',
    'numpy>=1.19.0',
    'pandas>=1.2.0',
    'pint>=0.17',
    'pint-pandas>=0.2',
    'pydot>=1.4.0',
    'pytest>=6.1.1',
    'semver>=2.8.0',
    'sphinx>=3.5.0'
    'sphinx-argparse>=0.2.0',
    'sphinx-rtd-theme>=0.4.0',
    'thermosteam>=0.25.4',
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
