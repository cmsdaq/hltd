#! /usr/bin/env python
"""WSDL parsing services package for Web Services for Python."""

ident = "$Id$"

#@SM: removed pbr dependency as it pulls a number of packages, including even git
#from pbr.version import VersionInfo
from . import WSDLTools  # noqa
from . import XMLname   # noqa

#_v = VersionInfo('wstools').semantic_version()
#__version__ = _v.release_string()
#version_info = _v.version_tuple()

__version__ = "0.4.8"
version_info = (0,4,8)

__all__ = (
    'WDSLTools',
    'XMLname',
   '__version__',
    'version_info'
)
