#!/usr/bin/env python

from distutils.core import setup

setup(
    name='jupyterhub-entrypoint',
    version='0.0.2',
    description='JupyterHub Custom Entrypoint Service',
    author='Josh Geden',
    author_email='jgeden@lbl.gov',
    url='https://github.com/NERSC/jupyterhub-entrypoint',
    packages=['jupyterhub_entrypoint', 'jupyterhub_entrypoint.dbi'],
    data_files=[("share/jupyterhub/entrypoint/templates", [
        "templates/about.html",
        "templates/index.html",
        "templates/error-no-tags.html",
        "templates/manage.html"
    ])]
)
