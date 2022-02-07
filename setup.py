from os import path
import sys
from setuptools import setup, find_packages

#read contents of README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(name = 'OpenRS',
    version = '0.3.2',
    description = 'Open Residual Stress analysis suite',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url = 'https://github.com/majroy/OpenRS',
    author = 'M J Roy',
    author_email = 'matthew.roy@manchester.ac.uk',

    classifiers=[
        'Environment :: Win32 (MS Windows)',
        'Topic :: Scientific/Engineering :: Visualization',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: Microsoft :: Windows :: Windows 7',
        'Programming Language :: Python :: 3.8',
        'Intended Audience :: End Users/Desktop',
        'Natural Language :: English',
        ],

    install_requires=['numpy','vtk', 'matplotlib', 'PyQt5>=5.13', 'h5py', 'pyyaml>=5.0', 'scipy'],
    license = 'Creative Commons Attribution-Noncommercial-Share Alike license',
    python_requires='>=3.8',
    packages=['OpenRS', 'OpenRS.geometry', 'OpenRS.examples',  'OpenRS.generate', 'OpenRS.meta'],
    package_data = {'OpenRS' : ['README.MD',], 'OpenRS.geometry' : ['*.*',], 'OpenRS.examples' : ['*.*',], 'OpenRS.generate' : ['*.*',], 'OpenRS.meta' : ['*.*',]},
    include_package_data=True
    )
