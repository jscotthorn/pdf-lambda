#!/bin/bash

# Create a virtual environment and install the required packages into it.
python3 -m virtualenv venv
source venv/bin/activate
python3 -m pip install -r ./requirements.txt

# Copy the required packages into somewhere to deploy
mkdir python
cp -r venv/lib/python3.9/site-packages/PyMuPDF* python/.
cp -r venv/lib64/python3.9/site-packages/fitz python/.
cp -r venv/lib64/python3.9/site-packages/fitz_old python/.

# Delete the superfluous pycache stuff
python3 -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
python3 -c "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"

# Zip it all up into a layer
zip -r layer.zip python

