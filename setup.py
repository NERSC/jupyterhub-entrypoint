#!/usr/bin/env python

from distutils.core import setup

setup(
        name='jupyterhub-entrypoint',
        version='0.0.0',
        description='JupyterHub Custom Entrypoint Service',
        author='Josh Geden',
        author_email='jgeden@lbl.gov',
        packages=['jupyterhub_entrypoint'],
        data_files=[("share/jupyterhub/entrypoint/templates", 
            ["templates/index.html"])]
)