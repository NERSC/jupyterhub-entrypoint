#!/usr/bin/env python

from distutils.core import setup

setup(
        name='jupyterhub-entrypoint',
        version='0.0.2',
        description='JupyterHub Custom Entrypoint Service',
        author='Josh Geden',
        author_email='jgeden@lbl.gov',
        url='https://github.com/Josh0823/jupyterhub-entrypoint',
        packages=['jupyterhub_entrypoint'],
        data_files=[("share/jupyterhub/entrypoint/templates", 
            ["templates/index.html"])]
)