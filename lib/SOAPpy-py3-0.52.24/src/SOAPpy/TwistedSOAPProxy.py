# twisted imports
from twisted.web import client

import SOAPpy


class TwistedSOAPProxy:
    """A Proxy for making remote SOAP calls.
    Pass the URL of the remote SOAP server to the constructor.
    Use proxy.callRemote('foobar', 1, 2) to call remote method
    'foobar' with args 1 and 2, proxy.callRemote('foobar', x=1)
    will call foobar with named argument 'x'.
    """

    # at some point this should have encoding etc. kwargs
    def __init__(self, url, namespace=None, header=None):
        self.url = url
        self.namespace = namespace
        self.header = header

    def _cbGotResult(self, result):
        result = SOAPpy.parseSOAPRPC(result)
        if hasattr(result, 'Result'):
            return result.Result
        elif len(result) == 1:
            ## SOAPpy 0.11.6 wraps the return results in a containing structure.
            ## This check added to make Proxy behaviour emulate SOAPProxy, which
            ## flattens the structure by default.
            ## This behaviour is OK because even singleton lists are wrapped in
            ## another singleton structType, which is almost always useless.
            return result[0]
        else:
            return result

    def callRemote(self, method: str, *args, **kwargs):
        payload = SOAPpy.buildSOAP(args=args, kw=kwargs, method=method,
                                   header=self.header, namespace=self.namespace)
        return client.getPage(self.url.encode, postdata=payload, method=b"POST",
                              headers={b'content-type': b'text/xml',
                                       b'SOAPAction': method.encode()}
                              ).addCallback(self._cbGotResult)
