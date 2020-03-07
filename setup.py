import setuptools
from serverly import version, description

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="serverly",
    version=version,
    author="mithem",
    author_email="miguel.themann@gmail.com",
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mithem/PyServer",
    packages=["serverly"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
