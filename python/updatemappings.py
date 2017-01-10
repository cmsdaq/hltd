#!/bin/env python

import sys#,traceback
import os

import mappings

import requests
import simplejson as json

class elasticUpdater:

    def __init__(self):
        if len(sys.argv)<2:
          print "Usage: python updatemappings.py central-es-hostname subsystem (e.g. es-vm-cdaq-01 cdaq)"
          os._exit(0)
        self.url=sys.argv[1]
        self.runindex_name="runindex_"+sys.argv[2]
        self.boxinfo_name="boxinfo_"+sys.argv[2]
        self.hltdlogs_name="hltdlogs_"+sys.argv[2]
        self.updateIndexMappingMaybe(self.runindex_name,mappings.central_runindex_mapping)
        self.updateIndexMappingMaybe(self.boxinfo_name,mappings.central_boxinfo_mapping)
        self.updateIndexMappingMaybe(self.hltdlogs_name,mappings.central_hltdlogs_mapping)

    def updateIndexMappingMaybe(self,index_name,mapping):
        #update in case of new documents added to mapping definition
        def updForKey(key):
            doc = {key:mapping[key]}
#            for d in doc[key]['properties']:
#              if 'type' in doc[key]['properties'][d] and doc[key]['properties'][d]['type']=='date':
#                if 'format' not in doc[key]["properties"][d]:
#                  doc[key]["properties"][d]['format']="epoch_millis||dateOptionalTime"

            res = requests.post('http://'+self.url+':9200/'+index_name+'/_mapping/'+key,json.dumps(doc))
            if res.status_code==200:
              print index_name,key
            else:
#              res_c = json.loads(res.content)
#              for ret_err in  res_c["error"]["root_cause"]:
#                  if ret_err["reason"].startswith("Mapper for [fm_date] conflicts with existing mapping in other types"):
#                      print "    ",index_name,key," has type conflict for fm_date. trying another format"
#                      doc[key]["properties"]["fm_date"]["format"]="epoch_millis||dateOptionalTime"
#
#                  elif ret_err["reason"].startswith("Mapper for [date] conflicts with existing mapping in other types"):
#                      print "    ",index_name,key," has type conflict for date. trying another format"
#                      #if format in doc["properties"]["fm_date"]:
#                      #  del doc["properties"]["fm_date"]["format"]
#                      doc[key]["properties"]["date"]["format"]="epoch_millis||dateOptionalTime"
#              
#                  else:
#                      print "ERROR:",index_name,key,'. return code:',res.status_code,ret_err
#              res = requests.post('http://'+self.url+':9200/'+index_name+'/_mapping/'+key,json.dumps(doc))
#              if res.status_code==200:
#                print index_name,key,res.status_code
#              else:
#                res_c = json.loads(res.content)
#                for ret_err in  res_c["error"]["root_cause"]:
#                  if ret_err["reason"].startswith("Mapper for [fm_date] conflicts with existing mapping in other types"):
#                      print "    ",index_name,key," has type conflict for fm_date (2). trying another format"
#                      doc[key]["properties"]["fm_date"]["format"]="strict_epoch_millis||dateOptionalTime"
#                  elif ret_err["reason"].startswith("Mapper for [date] conflicts with existing mapping in other types"):
#                      print "    ",index_name,key," has type conflict for date (2). trying another format"
#                      #if format in doc["properties"]["fm_date"]:
#                      #  del doc["properties"]["fm_date"]["format"]
#                      doc[key]["properties"]["date"]["format"]="strict_epoch_millis||dateOptionalTime"
#                  else:
#                      print "ERROR:",index_name,key,'. return code:',res.status_code,ret_err
#                res = requests.post('http://'+self.url+':9200/'+index_name+'/_mapping/'+key,json.dumps(doc))
#                if res.status_code==200:
#                  print index_name,key,res.status_code
#                else:
                  print "FAILED"
                  print index_name,key,res.status_code,res.content


        for mkey in mapping:
            if mkey=='run':continue
            updForKey(mkey)
        #run document. should not be written to a new index unless all parent-child relations have previously been set
        for mkey in mapping:
            if mkey!='run':continue
            updForKey(mkey)

if __name__ == "__main__":

    es = elasticUpdater()

    os._exit(0)
