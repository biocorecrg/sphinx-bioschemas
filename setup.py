from setuptools import setup

setup(
    name='sphinx-bioschemas',
    version='0.1',
    packages=['sphinx_bioschemas'],
    package_dir={'': 'src'},
    install_requires=[
        'sphinx',
    ],
)
