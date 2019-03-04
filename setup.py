from setuptools import setup, find_packages
from glob import glob


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='librelaws',
    version='0.1.0',
    description='Download German law texts and create a git like structure from them over time',
    long_description=readme,
    author='Christian Bourjau',
    author_email='c.bourjau@posteo.de',
    url='https://github.com/librelaws/librelaws',
    license=license,
    scripts=glob('scripts/*'),
    packages=find_packages(exclude=('tests', ))
)
