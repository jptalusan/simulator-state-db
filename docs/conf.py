# Minimal Sphinx configuration
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath('..'))

project = 'simulation-db'
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # for Google / NumPy style
    "sphinx.ext.viewcode",
]

authors = ['Your Name']
master_doc = 'index'
html_theme = 'sphinx_rtd_theme'
