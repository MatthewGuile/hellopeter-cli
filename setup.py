#!/usr/bin/env python3
"""
Setup script for the Hellopeter CLI package.
"""
import os
from setuptools import setup, find_packages

# Get the long description from the README file
with open(os.path.join(os.path.dirname(__file__), "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Get version from the package (Adjust path for src layout)
init_path = os.path.join("src", "hellopeter_cli", "__init__.py")
version = "0.0.0" # Default version if file not found or version missing
try:
    with open(init_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                version = line.split("=")[1].strip().strip('"\'')
                break
except FileNotFoundError:
    print(f"Warning: Could not find {init_path} to read version.")

# Tell setuptools where the package code is (src directory)
package_dir = {"": "src"}

setup(
    name="hellopeter-cli",
    version=version,
    description="A command-line tool for extracting reviews and statistics from Hellopeter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Matthew Guile",
    author_email="guile.matthew@gmail.com",
    url="https://github.com/MatthewGuile/hellopeter-cli",
    package_dir=package_dir,
    packages=find_packages(where="src"),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "hellopeter-cli=hellopeter_cli.cli:main",
        ],
    },
    install_requires=[
        "requests>=2.31.0",
        "SQLAlchemy>=2.0.23",
        "pandas>=2.1.1",
        "tqdm>=4.66.1",
        "backoff>=2.2.1",
    ],
    extras_require={
        'test': [
            'pytest>=7.0.0',
            'pytest-mock>=3.10.0',
            'responses>=0.25.0',
            'requests-mock>=1.11.0',
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12"
    ],
    python_requires=">=3.8",
    keywords="Hellopeter, reviews, statistics, api, cli, data extraction, web scraping, python",
    project_urls={
        "Bug Reports": "https://github.com/MatthewGuile/Hellopeter-cli/issues",
        "Source": "https://github.com/MatthewGuile/Hellopeter-cli",
    },
) 