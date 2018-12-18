import logging
try:
  from CGIHTTPServer import CGIHTTPRequestHandler
except:
  from http.server import CGIHTTPRequestHandler
  #handler = CGIHTTPServer.CGIHTTPRequestHandler

class WebCtrl(CGIHTTPRequestHandler):

    def __init__(self,hltd):
        self.logger = logging.getLogger(self.__class__.__name__)
        CGIHTTPRequestHandler.__init__(self)
        self.hltd = hltd

    def send_head(self):

        #if request is not cgi, handle internally
        if not super(CGIHTTPRequestHandler,self).is_cgi():
            path_pieces = self.path.split('/')[-1]
            if len(path_pieces)>=2:
              if path_pieces[-2]=='ctrl':
                  try:
                      #call hltd hook
                      self.hltd.webHandler(path_pieces[-1])
                  except Exception as ex:
                      self.logger.warning('Ctrl HTTP handler error: '+str(ex))
              else:
                  super(CGIHTTPRequestHandler,self).get_head()
             
        else:
            #call CGI handler
            super(CGIHTTPRequestHandler,self).get_head()
