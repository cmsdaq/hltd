try:
    import pkg_resources
    __version__ = pkg_resources.get_distribution("SOAPpy-py3").version
except:
    __version__="xxx"
