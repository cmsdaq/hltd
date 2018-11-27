#!/bin/env python

import sys#,traceback
import os

import mappings

import requests
try:
  import simplejson as json
except:
  import json

class elasticUpdater:

    def __init__(self):
        if len(sys.argv)<2:
          print "Usage:"
          print "  for runindex, boxinfo and hltdlogs indices:"
          print "       python updatemappings.py central-es-hostname subsystem"
          print "       (es-vm-cdaq-01 cdaq)"
          print "  or use this syntax to specify exact index names for runindex,boxinfo and hltdlogs:"
          print "       python updatemappings.py central-es-hostname null runindex_index boxinfo_index hltdlogs_index"
          print "       (es-vm-cdaq-01 auto runindex_cdaq_20170101 boxinfo_cdaq_20170101 hltdlogs_cdaq_20170101)"
          print "  or for copying mapping from one index to another:"
          print "       python updatemappings.py central-es-hostname subsystem input_index_mapping target_index"
          print "       (es-vm-cdaq-01 copy runindex_cdaq merging_cdaq)"
          print " or for setting up subsystem aliases:"
          print "       python updatemappings.py central-es-hostname aliases subsystem runindex_index boxinfo_index hltdlogs_index merging_index"
          print "       (es-vm-cdaq-01 aliases cdaq runindex_cdaq_20170101 boxinfo_cdaq_20170101 hltdlogs_cdaq_20170101 merging_cdaq_20170101 2017)"
          os._exit(0)

        self.url=sys.argv[1]

        if sys.argv[2]=="auto":
          #update 3 explicitly specified indices
          self.updateIndexMappingMaybe(sys.argv[3],mappings.central_runindex_mapping)
          self.updateIndexMappingMaybe(sys.argv[4],mappings.central_boxinfo_mapping)
          self.updateIndexMappingMaybe(sys.argv[5],mappings.central_hltdlogs_mapping)
        elif sys.argv[2]=="copy":
          #copy single index mapping to another
          res = requests.get('http://'+self.url+':9200/'+sys.argv[3]+'/_mapping')
          if res.status_code==200:
            res_j = json.loads(res.content)
            for idx in res_j:
              #else:alias
              new_mapping = res_j[idx]['mappings']
              print idx
              self.updateIndexMappingMaybe(sys.argv[4],new_mapping)
              break
        elif sys.argv[2]=="aliases":
          res = requests.get('http://'+self.url+':9200/_aliases')
          aliases = json.loads(res.content)
          old_idx_list = []
          actions = []
          for idx in aliases:
            #print idx
            for alias in aliases[idx]["aliases"]:
              if alias in ['runindex_'+sys.argv[3],'runindex_'+sys.argv[3]+'_read','runindex_'+sys.argv[3]+'_write',
                           'boxinfo_'+sys.argv[3],'boxinfo_'+sys.argv[3]+'_read','boxinfo_'+sys.argv[3]+'_write',
                           'hltdlogs_'+sys.argv[3],'hltdlogs_'+sys.argv[3]+'_read','hltdlogs_'+sys.argv[3]+'_write',
                           'merging_'+sys.argv[3],'merging_'+sys.argv[3]+'_write']:
                actions.append({"remove":{"index":idx,"alias":alias}})
                old_idx_list.append(idx)

          actions.append({"add":{"alias":"runindex_"+sys.argv[3],"index":sys.argv[4]}})
          actions.append({"add":{"alias":"runindex_"+sys.argv[3]+"_read","index":sys.argv[4]}})
          actions.append({"add":{"alias":"runindex_"+sys.argv[3]+"_write","index":sys.argv[4]}})

          actions.append({"add":{"alias":"boxinfo_"+sys.argv[3],"index":sys.argv[5]}})
          actions.append({"add":{"alias":"boxinfo_"+sys.argv[3]+"_read","index":sys.argv[5]}})
          actions.append({"add":{"alias":"boxinfo_"+sys.argv[3]+"_write","index":sys.argv[5]}})

          actions.append({"add":{"alias":"hltdlogs_"+sys.argv[3],"index":sys.argv[6]}})
          actions.append({"add":{"alias":"hltdlogs_"+sys.argv[3]+"_read","index":sys.argv[6]}})
          actions.append({"add":{"alias":"hltdlogs_"+sys.argv[3]+"_write","index":sys.argv[6]}})

          actions.append({"add":{"alias":"merging_"+sys.argv[3],"index":sys.argv[7]}})
          actions.append({"add":{"alias":"runindex_"+sys.argv[3]+"_read","index":sys.argv[7]}}) #!
          actions.append({"add":{"alias":"merging_"+sys.argv[3]+"_write","index":sys.argv[7]}})

          #adding all-year index if required
          if len(sys.argv)>8 and sys.argv[8].isdigit():
              year_suffix = sys.argv[3]+sys.argv[8]
              actions.append({"add":{"alias":"runindex_"+year_suffix+"_read","index":sys.argv[4]}})
              actions.append({"add":{"alias":"boxinfo_" +year_suffix+"_read","index":sys.argv[5]}})
              actions.append({"add":{"alias":"hltdlogs_"+year_suffix+"_read","index":sys.argv[6]}})
              actions.append({"add":{"alias":"runindex_"+year_suffix+"_read","index":sys.argv[7]}}) #!

          data = json.dumps({"actions":actions})
          print data
          res = requests.post('http://'+self.url+':9200/_aliases',data)
          print res.status_code

          print "current",sys.argv[3],"alias removed from indices: ",",".join(set(old_idx_list)).strip('"')
          
          pass
        else:
          self.runindex_name="runindex_"+sys.argv[2]
          self.boxinfo_name="boxinfo_"+sys.argv[2]
          self.hltdlogs_name="hltdlogs_"+sys.argv[2]
          #update by alias
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
