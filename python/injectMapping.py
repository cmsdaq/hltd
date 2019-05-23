#!/bin/env python
from __future__ import print_function

import sys,traceback
import os
import datetime
import time

#from aUtils import *
import mappings

from elasticsearch import Elasticsearch
from elasticsearch.serializer import JSONSerializer

import requests
try:
  import simplejson as json
except:
  import json
import socket

jsonSerializer = JSONSerializer()

class elasticBandInjector:

    def __init__(self,es_server_url,subsys,update_run_mapping=True,update_box_mapping=True,update_logs_mapping=True):
        self.es_server_url=es_server_url
        self.runindex_write="runindex_"+subsys+"_write"
        self.runindex_read="runindex_"+subsys+"_read"
        self.runindex_name="runindex_"+subsys
        self.boxinfo_write="boxinfo_"+subsys+"_write"
        self.boxinfo_read="boxinfo_"+subsys+"_read"
        self.boxinfo_name="boxinfo_"+subsys
        self.hltdlogs_write="hltdlogs_"+subsys+"_write"
        self.hltdlogs_read="hltdlogs_"+subsys+"_read"
        self.hltdlogs_name="hltdlogs_"+subsys
        if update_run_mapping:
            self.updateIndexMaybe(self.runindex_name,self.runindex_write,self.runindex_read,mappings.central_es_settings_runindex,mappings.central_runindex_mapping)
        if update_box_mapping:
            self.updateIndexMaybe(self.boxinfo_name,self.boxinfo_write,self.boxinfo_read,mappings.central_es_settings_boxinfo,mappings.central_boxinfo_mapping)
        if update_logs_mapping:
            self.updateIndexMaybe(self.hltdlogs_name,self.hltdlogs_write,self.hltdlogs_read,mappings.central_es_settings_hltlogs,mappings.central_hltdlogs_mapping)
        #silence

    def updateIndexMaybe(self,index_name,alias_write,alias_read,settings,mapping):
        self.es = Elasticsearch(self.es_server_url,timeout=20) #is this needed? (using requests)

        #using this now for transition to elasticsearch7
        if self.es.info()['version']['number'].startswith('6'):
          essuffix = ''
        else:
          essuffix = '?include_type_name=true'
 
        if requests.get(self.es_server_url+'/_alias/'+alias_write).status_code == 200:
            print('writing to elastic index '+alias_write + ' on '+self.es_server_url+' - '+self.es_server_url)
            self.createDocMappingsMaybe(alias_write,mapping,essuffix)

    def createDocMappingsMaybe(self,index_name,mapping,essuffix=''):
        #update in case of new documents added to mapping definition

        for key in mapping:
            doc = {key:mapping[key]}
            res = requests.get(self.es_server_url+'/'+index_name+'/'+key+'/_mapping'+essuffix)
            #only update if mapping is empty
            if res.status_code==200:
                if res.content.decode().strip()=='{}':
                    print('inserting new mapping for '+str(key))
                    res = requests.post(self.es_server_url+'/'+index_name+'/'+key+'/_mapping'+essuffix,jsonSerializer.dumps(doc),headers={'Content-Type':'application/json'})
                else:
                    #still check if number of properties is identical in each type
                    inmapping = json.loads(res.content)
                    for indexname in inmapping:
                        properties = inmapping[indexname]['mappings'][key]['properties']

                        print('checking mapping '+ indexname + '/' + key + ' which has ' + str(len(mapping[key]['properties'])) + '(index:' + str(len(properties)) + ') entries..')
                        try_inject=False
                        for pdoc in mapping[key]['properties']:
                            if pdoc not in properties:
                                try_inject=True
                                print('inserting mapping for ' + str(key) + ' which is missing mapping property ' + str(pdoc))
                        if try_inject:
                            rres = requests.post(self.es_server_url+'/'+index_name+'/'+key+'/_mapping'+essuffix,jsonSerializer.dumps(doc),headers = {'Content-Type':'application/json'})
                            if rres.status_code!=200:
                                print(rres.content)
            else:
                print('requests error code '+res.status_code+' in mapping request')

if __name__ == "__main__":

    print("Elastic mapping injector. Parameters: server URL, subsystem name, all|run|box|log")
    url = sys.argv[1]
    if not url.startswith('http://'):url='http://'+url
    subsys = sys.argv[2]
    upd_run = sys.argv[3]=='all' or sys.argv[3]=='run'
    upd_box = sys.argv[3]=='all' or sys.argv[3]=='box'
    upd_log = sys.argv[3]=='all' or sys.argv[3]=='log'
    es = elasticBandInjector(url,subsys,upd_run,upd_box,upd_log)

    print("Quit")
    os._exit(0)
