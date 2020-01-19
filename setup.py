import setuptools

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="asyncnetfsm",
    version="0.0.12",
    author="Omar Al-Ghussein",
    author_email="z3@live.it",
    description="simply its Netdev with textFSM ",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/omaralghussein/asyncnetfsm",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)