import os,socket,time
import sys
import threading

from elasticsearch import Elasticsearch
from elasticsearch.serializer import JSONSerializer
from elasticsearch.exceptions import (ConnectionError, ConnectionTimeout,
                                      TransportError, SerializationError)

import simplejson as json
import csv
import math
import logging
import copy

from aUtils import *
from elasticTemplates import runappliance

fuout_doc_id = True

def getURLwithIP(url):
    try:
        prefix = ''
        if url.startswith('http://'):
            prefix='http://'
            url = url[7:]
        suffix=''
        port_pos=url.rfind(':')
        if port_pos!=-1:
            suffix=url[port_pos:]
            url = url[:port_pos]
    except Exception as ex:
        logging.error('could not parse URL ' +url)
        raise ex
    if url!='localhost':
        ip = socket.gethostbyname(url)
    else: ip='127.0.0.1'

    return prefix+str(ip)+suffix

def getCPUInfoIntel():
    cpu_name = ""
    try:
        with open('/proc/cpuinfo','r') as fi:
            for line in fi.readlines():
                if line.startswith("model name") and not cpu_name:
                    for word in line[line.find(':')+1:].split():
                        if word=='' or '(R)' in word  or '(TM)' in word or 'CPU' in word or '@' in word :continue
                        if 'GHz' in word: pass
                        else:
                            if cpu_name: cpu_name = cpu_name+" "+word
                            else: cpu_name=word
    finally:
        return cpu_name

jsonSerializer = JSONSerializer()

def bulk_index(es, index, documents):# query_params=None): #todo:ass kwargs

        body_tmp = []
        if not documents:
            raise ValueError('No document array provided for bulk_index operation')

        for doc in documents:
            desc_tmp = {'index': {'_index': index}}
            try:
              desc_tmp['index']['_id']=doc.pop('_id')
            except:
              pass
            #body_tmp.append(jsonSerializer.dumps({'index': {'_index': index}}))
            body_tmp.append(jsonSerializer.dumps(desc_tmp))
            body_tmp.append(jsonSerializer.dumps(doc))

        # Need the trailing newline.
        body = '\n'.join(body_tmp) + '\n'
        #return es.bulk(body=body,query_params=query_params)
        return es.bulk(body=body)


class elasticBand():


    def __init__(self,es_server_url,runstring,indexSuffix,monBufferSize,fastUpdateModulo,forceReplicas,forceShards,nprocid=None,bu_name="unknown"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.es_server_url = es_server_url
        self.istateBuffer = []
        self.prcinBuffer = {}
        self.prcoutBuffer = {}
        self.fuoutBuffer = {}
        self.prcsstateBuffer = {}
        self.procmonBuffer = {}

        self.es = Elasticsearch(self.es_server_url,timeout=20)
        eslib_logger = logging.getLogger('elasticsearch')
        eslib_logger.setLevel(logging.ERROR)

        #self.hostip = socket.gethostbyname_ex(self.hostname)[2][0]
        #self.number_of_data_nodes = self.es.health()['number_of_data_nodes']
        #self.settings = {     "index.routing.allocation.require._ip" : self.hostip }

        self.indexName = runstring + "_" + indexSuffix
        try:
            body = copy.deepcopy(runappliance)
            #filepath = os.path.join(os.path.dirname((os.path.realpath(__file__))),'../json',"runapplianceTemplate.json")
            #with open(filepath,'r') as fpi:
            #    body = json.load(fpi)
            if forceReplicas>=0:
                body['settings']['index']['number_of_replicas']=forceReplicas
            if forceShards>=0:
                body['settings']['index']['number_of_shards']=forceShards

            body.pop('index_patterns')

            c_res = self.es.indices.create(self.indexName, body = body)

            if 'acknowledged' in c_res and c_res['acknowledged']==True:
                self.logger.info("Result of index create: " + str(c_res) )
        except Exception as ex:
            self.logger.info("Elastic Exception "+ str(ex))

        self.indexFailures=0
        self.monBufferSize = monBufferSize
        self.fastUpdateModulo = fastUpdateModulo
        self.hostname = os.uname()[1]
        self.sourceid = self.hostname + '_' + str(os.getpid())
        #construct id string (num total (logical) cores and num_utilized cores
        cpu_name = getCPUInfoIntel() 
        if cpu_name and nprocid: nprocid = nprocid+"_"+cpu_name
        self.nprocid = nprocid
        self.bu_name = bu_name

    def setCentral(self,central):
        self.es_central = Elasticsearch(central,timeout=20)

    def imbue_jsn(self,infile,silent=False):
        with open(infile.filepath,'r') as fp:
            try:
                document = json.load(fp)
            except json.scanner.JSONDecodeError as ex:
                if silent==False:
                    self.logger.exception(ex)
                return None,-1
            return document,0

    def imbue_csv(self,infile):
        with open(infile.filepath,'r') as fp:
            fp.readline()
            row = fp.readline().strip('\n').split(',')
            return row

    def elasticize_prc_istate(self,infile):
        filepath = infile.filepath
        self.logger.debug("%r going into buffer" %filepath)
        #mtime = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(os.path.getmtime(filepath)))
        mtime = infile.mtime
        stub = self.imbue_csv(infile)
        document = {}
        if len(stub) == 0 or stub[0]=='\n':
            return;
        document['doc_type'] = 'prc-i-state'
        try:
            document['macro'] = int(stub[0])
            document['mini']  = int(stub[1])
            document['micro'] = int(stub[2])
            document['tp']    = float(stub[4])
            document['lead']  = float(stub[5])
            document['nfiles']= int(stub[6])
            document['lockwaitUs']  = float(stub[7])
            document['lockcount']  = float(stub[8])
            try:document['nevents']= int(stub[3])
            except:pass
            try:document['instate']= int(stub[9])
            except:pass
            document['fm_date'] = str(mtime)
            document['mclass'] = self.nprocid
            if infile.tid:
              document['source'] = self.hostname + '_' + infile.pid + '_' + infile.tid
            else:
              document['source'] = self.hostname + '_' + infile.pid
            self.istateBuffer.append(document)
        except Exception as ex:
            self.logger.warning(str(ex))
            pass
        #if len(self.istateBuffer) == MONBUFFERSIZE:
        if len(self.istateBuffer) == self.monBufferSize and (len(self.istateBuffer)%self.fastUpdateModulo)==0:
            self.flushMonBuffer()

    def elasticize_prc_sstate(self,infile):
        document,ret = self.imbue_jsn(infile)
        if ret<0:return
        datadict = {}
        datadict['doc_type'] = 'prc-s-state'
        datadict['host']=self.hostname
        datadict['pid']=int(infile.pid[3:])
        try:datadict['tid']=int(infile.tid[3:])
        except:pass
        datadict['ls'] = int(infile.ls[2:])
        if document['data'][0] != "N/A":
            datadict['macro']   = [int(f) for f in document['data'][0].strip('[]').split(',')]
            #datadict['macro_s']   = [int(f) for f in document['data'][0].strip('[]').split(',')]
        else:
            datadict['macro'] = -1
            #datadict['macro_s'] = -1
        if document['data'][1] != "N/A":
            miniVector = []
            for idx,f in enumerate(document['data'][1].strip('[]').split(',')):
                val = int(f)
                if val>0:miniVector.append({'key':idx,'value':val})
            datadict['miniv']   = miniVector
        else:
            datadict['miniv'] = []
        if document['data'][2] != "N/A":
            microVector = []
            for idx,f in enumerate(document['data'][2].strip('[]').split(',')):
                val = int(f)
                if val>0:microVector.append({'key':idx,'value':val})
            datadict['microv']   = microVector
        else:
            datadict['microv'] = []
        try:
            datadict['inputStats'] = {
              'tp' :   float(document['data'][4]) if not math.isnan(float(document['data'][4])) and not  math.isinf(float(document['data'][4])) else 0.,
              'lead' : float(document['data'][5]) if not math.isnan(float(document['data'][5])) and not  math.isinf(float(document['data'][5])) else 0.,
              'nfiles' :  int(document['data'][6]),
              'lockwaitUs' : float(document['data'][7]),
              'lockcount' : float(document['data'][8]),
              'nevents' : int(document['data'][3])
            }
            try:
              if document['data'][9] != "N/A":
                inVector = []
                for idx,f in enumerate(document['data'][9].strip('[]').split(',')):
                  val = int(f)
                  if val>0 and idx>0:inVector.append({'key':idx,'value':val})
                datadict['inputStats']['instatev']=inVector
              else:
                datadict['instatev'] = []
            except:
              pass
        except:
            pass
        datadict['fm_date'] = str(infile.mtime)
        #per-thread source field if CMSSW is configured to provide per-thread json
        if infile.tid:
          datadict['source'] = self.hostname + '_' + infile.pid + '_' + infile.tid
        else:  
          datadict['source'] = self.hostname + '_' + infile.pid
        datadict['mclass'] = self.nprocid
        #datadict['fm_date_s'] = str(infile.mtime)
        #datadict['source_s'] = self.hostname + '_' + infile.pid
        #datadict['mclass_s'] = self.nprocid
        #self.tryIndex('prc-s-state',datadict)
        self.prcsstateBuffer.setdefault(infile.ls,[]).append(datadict)

    def elasticize_prc_procmon(self,infile):
        document,ret = self.imbue_jsn(infile)
        if ret<0:return
        self.procmonBuffer.setdefault(infile.ls,[]).append(document)

    def mergeAndIndexProcmon(self,buf):
        mdoc = {}
        for doc in buf:
          try:
            mdoc["doc_type"]=doc["doc_type"]
            #mdoc.setdefault("pid",[]).append(doc["pid"])
            mdoc["host"]=doc["host"]
            mdoc["run"]=doc["run"]
            mdoc["ls"]=doc["ls"]
            mdoc.setdefault("delta_ls",[]).append(doc["delta_ls"])
            if "date" in mdoc:mdoc["date"] =min(mdoc["date"],doc["date"])
            else:mdoc["date"]=doc["date"]
            mdoc.setdefault("m_id",[]).append(doc["m_id"])
          except Exception as ex:
            self.logger.exception(ex)
        mdoc["m_id"] = list(set(mdoc["m_id"]))
        try:
          self.es_central.index(index='test_conddb',body=mdoc)
        except (ConnectionError,ConnectionTimeout) as ex:
            self.logger.warning("Elasticsearch connection error (test_conddb):"+str(ex))
        except SerializationError as ex:
            self.logger.warning("Elasticsearch serializer error (test_conddb):"+str(ex))
        except TransportError as ex:
            self.logger.warning("Elasticsearch http error (test_conddb):"+str(ex))

    def elasticize_prc_out(self,infile):
        document,ret = self.imbue_jsn(infile)
        if ret<0:return
        run=infile.run
        ls=infile.ls
        stream=infile.stream
        #removing 'stream' prefix
        document['doc_type'] = 'prc-out'
        if stream.startswith("stream"): stream = stream[6:]
        try:
          document['din']=int(document["data"][0])
          document['dout']=int(document["data"][1])
        except Exception as ex:
          self.logger.warning(str(ex))
        try:document.pop('data')
        except:pass
        document['lsn']=int(ls[2:])
        document['streamn']=stream
        document['pidn']=int(infile.pid[3:])
        document['hostn']=self.hostname
        document['appn']=self.bu_name
        document['fm_d']=int(infile.mtimems)

        #document['ls']=int(ls[2:])
        #document['stream']=stream
        #document['pid']=int(infile.pid[3:])
        #document['host']=self.hostname
        #document['appliance']=self.bu_name
        #document['fm_date']=str(infile.mtime)

        try:document.pop('definition')
        except:pass
        try:document.pop('source')
        except:pass
        self.prcoutBuffer.setdefault(ls,[]).append(document)
        #self.es.index(self.indexName,'prc-out',document)
        #return int(ls[2:])

    def elasticize_fu_out(self,infile):

        document,ret = self.imbue_jsn(infile)
        if ret<0:return
        run=infile.run
        ls=infile.ls
        stream=infile.stream
        document['doc_type'] = 'fu-out'
        #removing 'stream' prefix
        if stream.startswith("stream"): stream = stream[6:]
        #TODO:read output jsd file to decide on the variable format
        values = [int(f) if ((type(f) is str and f.isdigit()) or type(f) is int) else str(f) for f in document['data']]
        if len(values)>10:
            keys = ["in","out","errorEvents","returnCodeMask","Filelist","fileSize","InputFiles","fileAdler32","TransferDestination","MergeType","hltErrorEvents"]
        elif len(values)>9:
            keys = ["in","out","errorEvents","returnCodeMask","Filelist","fileSize","InputFiles","fileAdler32","TransferDestination","hltErrorEvents"]
        else:
            keys = ["in","out","errorEvents","returnCodeMask","Filelist","fileSize","InputFiles","fileAdler32","TransferDestination"]
        datadict = dict(zip(keys, values))
        try:datadict.pop('Filelist')
        except:pass
        document['data']=datadict
        document['ls']=int(infile.ls[2:])
        document['stream']=stream
        #document['source']=self.hostname
        document['host']=self.hostname
        document['appliance']=self.bu_name
        document['fm_date']=str(infile.mtime)
        if fuout_doc_id:
          document['_id']="_".join(("fu_out",run,ls,stream,self.hostname))
        try:document.pop('definition')
        except:pass
        try:document.pop('source')
        except:pass
        self.fuoutBuffer.setdefault(ls,[]).append(document)
        #self.es.index(self.indexName,'fu-out',document)

    def elasticize_prc_in(self,infile):
        document,ret = self.imbue_jsn(infile)
        if ret<0:return
        document['doc_type'] = 'prc-in'
        document['data'] = [int(f) if f.isdigit() else str(f) for f in document['data']]
        try:
            data_size=document['data'][1]
        except:
            data_size=0
        datadict = {'out':document['data'][0],'size':data_size}
        document['data']=datadict
        document['ls']=int(infile.ls[2:])
        document['index']=int(infile.index[5:])
        document['pid']=int(infile.pid[3:])
        document['host']=self.hostname
        document['appliance']=self.bu_name
        document['fm_date']=str(infile.mtime)
        try:document.pop('definition')
        except:pass
        try:document.pop('source')
        except:pass
        #self.prcinBuffer.setdefault(ls,[]).append(document)
        self.tryBulkIndex('prc-in',[document],attempts=5)

    def elasticize_queue_status(self,infile):
        return True #disabling this message
        document,ret = self.imbue_jsn(infile,silent=True)
        if ret<0:return False
        document['doc_type'] = 'qstatus'
        document['fm_date']=str(infile.mtime)
        document['host']=self.hostname
        self.tryIndex(document)
        return True

    def elasticize_fu_complete(self,timestamp):
        document = {}
        document['doc_type'] = 'fu-complete'
        document['host']=self.hostname
        document['fm_date']=timestamp
        self.tryBulkIndex('fu-complete',[document],attempts=5)

    def flushMonBuffer(self):
        if self.istateBuffer:
            self.logger.info("flushing fast monitor buffer (len: %r) " %len(self.istateBuffer))
            self.tryBulkIndex('prc-i-state',self.istateBuffer,attempts=2,logErr=False)
            self.istateBuffer = []

    def flushLS(self,ls):
        self.logger.info("flushing %r" %ls)
        prcinDocs = self.prcinBuffer.pop(ls) if ls in self.prcinBuffer else None
        prcoutDocs = self.prcoutBuffer.pop(ls) if ls in self.prcoutBuffer else None
        fuoutDocs = self.fuoutBuffer.pop(ls) if ls in self.fuoutBuffer else None
        prcsstateDocs = self.prcsstateBuffer.pop(ls) if ls in self.prcsstateBuffer else None
        procmonDocs = self.procmonBuffer.pop(ls) if ls in self.procmonBuffer else None
        if prcinDocs: self.tryBulkIndex('prc-in',prcinDocs,attempts=5)
        if prcoutDocs: self.tryBulkIndex('prc-out',prcoutDocs,attempts=5)
        if fuoutDocs: self.tryBulkIndex('fu-out',fuoutDocs,attempts=10)
        if prcsstateDocs: self.tryBulkIndex('prc-s-state',prcsstateDocs,attempts=5,logErr=False)
        if procmonDocs: self.mergeAndIndexProcmon(procmonDocs)

    def flushAllLS(self):
        lslist = list(  set(self.prcinBuffer.keys()) |
                        set(self.prcoutBuffer.keys()) |
                        set(self.fuoutBuffer.keys()) |
                        set(self.prcsstateBuffer.keys()) |
                        set(self.procmonBuffer.keys()))
        for ls in lslist:
            self.flushLS(ls)

    def flushAll(self):
        self.flushMonBuffer()
        self.flushAllLS()

    def tryIndex(self,document):
        try:
            self.es.index(index=self.indexName,body=document)
        except (ConnectionError,ConnectionTimeout) as ex:
            self.logger.warning("Elasticsearch connection error:"+str(ex))
            self.indexFailures+=1
            if self.indexFailures<2:
                self.logger.exception(ex)
            #    self.logger.warning("Elasticsearch connection error.")
            time.sleep(3)

        except SerializationError as ex:
            self.logger.warning("Elasticsearch serializer error:"+str(ex))
            self.indexFailures+=1
            if self.indexFailures<2:
                self.logger.exception(ex)
            time.sleep(.1)

        except TransportError as ex:
            self.logger.warning("Elasticsearch http error:"+str(ex))
            self.indexFailures+=1
            if self.indexFailures<2:
                self.logger.exception(ex)
            time.sleep(.1)

    def tryBulkIndex(self,docname,documents,attempts=5,logErr=True):
        tried_ip_rotate = False
        while attempts>0 and len(documents):
            attempts-=1
            try:
                reply = bulk_index(self.es,self.indexName,documents)
                try:
                    if reply['errors']==True:
                        retry_doc = []
                        errors = []
                        unknown_errors=False
                        sleep_time=0.1 if attempts>0 else 0.2
                        for idx,item in enumerate(reply['items']):
                          bk_reply = item['index']
                          bk_status = bk_reply['status']
                          if bk_status==201 or bk_status==200:
                            continue
                          elif bk_status==409: #conflict, skip injection but log the warning
                            pass
                          elif bk_status==429:#rejected execution,retry with bigger sleep time
                            sleep_time=(2-attempts)*0.5 if attempts<2 else 0.2
                            retry_doc.append(documents[idx])
                          else:
                            unknown_errors=True
                            retry_doc.append(documents[idx])

                          errors.append([bk_reply['error']['type'],bk_reply['error']['reason'],bk_status])

                        if len(errors):
                          msg_err = "Error reply on bulk-index request, type "+str(docname)+", failed docs:"+str(len(errors))+'/'+str(len(documents))+ ': ' +str(errors) + ', left retries:'+str(attempts)
                          if (unknown_errors or attempts==0) and logErr==True:
                            self.logger.error(msg_err)
                          else:
                            self.logger.warning(msg_err)
                        documents = retry_doc

                        #sleep in case of error
                        time.sleep(sleep_time)
                    else:
                        documents = []
                        break

                except Exception as ex:
                    #failed to parse json reply from the server
                    try:
                      js_reply = json.dumps(reply)
                    except Exception as exc:
                      js_reply = str(exc)
                    self.logger.error("unable to parse error reply from elasticsearch: " + js_reply + " documents:"+str(len(documents)))

            except (ConnectionError,ConnectionTimeout) as ex:
                self.logger.warning("Elasticsearch connection error:"+str(ex)+ " attempts left:"+str(attempts) + " tried IP rotate:"+str(tried_ip_rotate))
                if attempts==0:
                    if not tried_ip_rotate:
                        #try another host before giving up
                        self.es=Elasticsearch(getURLwithIP(self.es_server_url),timeout=20)
                        tried_ip_rotate=True
                        attempts=1
                        continue

                    self.indexFailures+=1
                    if self.indexFailures<2:
                        if logErr:
                            self.logger.exception(ex)
                time.sleep(2)

            except SerializationError as ex:
                self.logger.warning("Elasticsearch serialization error:"+str(ex) + " attempts left:"+str(attempts))
                if attempts==0:
                    self.indexFailures+=1
                    if self.indexFailures<2:
                        if logErr:
                            self.logger.exception(ex)
                time.sleep(.1)
 
            except TransportError as ex:
                self.logger.warning("Elasticsearch http error:"+str(ex) + " attempts left:"+str(attempts))
                if attempts==0:
                    self.indexFailures+=1
                    if self.indexFailures<2:
                        if logErr:
                            self.logger.exception(ex)
                time.sleep(.1)

