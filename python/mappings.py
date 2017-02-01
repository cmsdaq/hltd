#!/bin/env python

central_es_settings_runindex = {
            "analysis":{
                "analyzer": {
                    "default": {
                        "type": "keyword"
                    }
                }
            },
            "index":{
                'number_of_shards' : 8,
                'number_of_replicas' : 2,
                'codec' : 'best_compression',
                'translog':{'durability':'async','flush_threshold_size':'4g'},
                'mapper':{'dynamic':'false'}
            }
        }


central_es_settings_boxinfo = {
            "analysis":{
                "analyzer": {
                    "default": {
                        "type": "keyword"
                    }
                }
            },
            "index":{
                'number_of_shards' : 8,
                'number_of_replicas' : 1,
                'codec' : 'best_compression',
                'translog':{'durability':'async','flush_threshold_size':'4g'},
                'mapper':{'dynamic':'false'}
            }
        }


central_es_settings_hltlogs = {

            "analysis":{
                "analyzer": {
                    "prefix-test-analyzer": {
                        "type": "custom",
                        "tokenizer": "prefix-test-tokenizer"
                    }
                },
                "tokenizer": {
                    "prefix-test-tokenizer": {
                        "type": "path_hierarchy",
                        "delimiter": " "
                    }
                }
            },
            "index":{
                'number_of_shards' : 8,
                'number_of_replicas' : 1,
                'codec' : 'best_compression',
                'translog':{'durability':'async','flush_threshold_size':'4g'},
                'mapper':{'dynamic':'false'}
            }
        }


central_runindex_mapping = {
            'run' : {
                'properties' : {
                    'runNumber':{
                        'type':'integer'
                        },
                    'startTimeRC':{
                        'type':'date'
                            },
                    'stopTimeRC':{
                        'type':'date'
                            },
                    'startTime':{
                        'type':'date'
                            },
                    'endTime':{
                        'type':'date'
                            },
                    'completedTime' : {
                        'type':'date'
                            },
                    'activeBUs':{
                        'type':'integer'
                    },
                    'totalBUs':{
                        'type':'integer'
                    },
                    'rawDataSeenByHLT':{
                        'type':'boolean'
                    },
                    'CMSSW_version':{
	              'type':'string','index':'not_analyzed'
                    },
                    'CMSSW_arch':{
	              'type':'string','index':'not_analyzed'
                    }
                }
            },
            'microstatelegend' : {
		'_all': {'enabled': "false" },
                '_parent':{'type':'run'},
                'properties' : {
	            'id':{'type':'string','index':'not_analyzed'},
                    'names':{
                        'type':'string',
                        "index":"not_analyzed"
                        },
                    'stateNames':{
                        'type':'string','index':'no'
                        },
                    'reserved':{
                        'type':'integer'
                        },
                    'special':{
                        'type':'integer'
                        },
                    'output':{
                        'type':'integer'
                        },
                    'fm_date':{
                        'type':'date'
                        }
                    }
            },
            'pathlegend' : {
		'_all': {'enabled': "false" },
                '_parent':{'type':'run'},
                'properties' : {
	            'id':{'type':'string','index':'not_analyzed'},
                    'names':{
                        'type':'string',
                        "index":"not_analyzed"
                        },
                    'stateNames':{
                        'type':'string','index':'no'
                        },
                    'reserved':{
                        'type':'integer'
                        },
                    'fm_date':{
                        'type':'date'
                        }
                    }
                },
            'inputstatelegend' : {
		 '_all': {'enabled': "false" },
                '_parent':{'type':'run'},
                'properties' : {
                    'stateNames':{
                        'type':'string','index':'no'
                        },
                    'fm_date':{
                        'type':'date'
                        }
                    }
                },
            'stream_label' : {
                '_all': {'enabled': "false" },
                '_parent':{'type':'run'},
                'properties' : {
                    'stream':{
                        'type':'string',
                        'index':'not_analyzed'
                        },
                    'fm_date':{
                        'type':'date'
                        },
                    'id'            :{'type':'string','index':'not_analyzed'}
                    }
                },
            'eols' : {
                '_all': {'enabled': "false" },
                '_parent'    :{'type':'run'},
                'properties' : {
                    'fm_date'       :{'type':'date'
                    },
                    'id'            :{'type':'string','index':'not_analyzed'},
                    'ls'            :{'type':'integer'},
                    'NEvents'       :{'type':'integer'},
                    'NFiles'        :{'type':'integer'},
                    'TotalEvents'   :{'type':'integer'},
                    'NLostEvents'   :{'type':'integer'},
                    'NBytes'        :{'type':'long'},
                    'appliance'     :{'type':'string','index' : 'not_analyzed'}
                    }
                },
            'minimerge' : {
                '_all': {'enabled': "false" },
                'properties' : {
                    'fm_date'       :{'type':'date'
                    },
                    'id'            :{'type':'string','index':'not_analyzed'}, #run + appliance + stream + ls
                    'appliance'     :{'type':'string','index':'not_analyzed'}, #wrong mapping:not analyzed
                    'host'          :{'type':'string','index' : 'not_analyzed'},
                    'stream'        :{'type':'string','index' : 'not_analyzed'},
                    'ls'            :{'type':'integer'},
                    'processed'     :{'type':'integer'},
                    'accepted'      :{'type':'integer'},
                    'errorEvents'   :{'type':'integer'},
                    'size'          :{'type':'long'},
		    'eolField1'     :{'type':'integer'},
		    'eolField2'     :{'type':'integer'},
		    'fname'         :{'type':'string','index':'not_analyzed'},
		    'adler32'       :{'type':'long'},
                    'runNumber'     :{'type':'integer'}
                    }
                },
            'macromerge' : {
                '_all': {'enabled': "false" },
                'properties' : {
                    'fm_date'       :{'type':'date'
                    },
                    'id'            :{'type':'string','index':'not_analyzed'}, #run + appliance + stream + ls
                    'appliance'     :{'type':'string','index':'not_analyzed'},
                    'host'          :{'type':'string','index' : 'not_analyzed'},
                    'stream'        :{'type':'string','index' : 'not_analyzed'},
                    'ls'            :{'type':'integer'},
                    'processed'     :{'type':'integer'},
                    'accepted'      :{'type':'integer'},
                    'errorEvents'   :{'type':'integer'},
                    'size'          :{'type':'long'},
		    'eolField1'     :{'type':'integer'},
		    'eolField2'     :{'type':'integer'},
		    'fname'         :{'type':'string','index':'not_analyzed'},
                    'runNumber'     :{'type':'integer'}
                    }
                },
            'stream-hist' : {
                    "_all":{
                            "enabled": "false"
                    },
                    "_parent": {
                            "type": "run"
                    },
                    "properties": {
                            "stream": {
                                    "type": "string",
                                    "index": "not_analyzed"
                            },
                            "ls": {
                                    "type": "integer"
                            },
                            "in": {
                                    "type": "float"
                            },
                            "out": {
                                    "type": "float"
                            },
                            "err": {
                                    "type": "float"
                            },
                            "filesize": {
                                    "type": "float"
                            },
                            "completion":{
                                    "type": "double"
                            },
                            "fm_date":{
                                    "type": "date"
                            },
                            "date":{
                                    "type": "date"
                            }
                    },
                },
	    "state-hist": {
		    '_all': {'enabled': "false" },
		    "_parent": {
			    "type": "run"
		    },
		    "properties": {
			    "hminiv": {
				    "properties": {
					    "entries": {
						    "properties": {
							    "key": {
								    "type": "short"
							    },
							    "count": {
								    "type": "integer"
							    }
						    }
					    },
					    "total": {
						    "type": "integer"
					    }
				    }
			    },
			    "hmicrov": {
				    "properties": {
					    "entries": {
						    "properties": {
							    "key": {
								    "type": "short"
							    },
							    "count": {
								    "type": "integer"
							    }
						    }
					    },
					    "total": {
						    "type": "integer"
					    }
				    }
			    },
			    "hmacrov": {
				    "properties": {
					    "entries": {
						    "properties": {
							    "key": {
								    "type": "short"
							    },
							    "count": {
								    "type": "integer"
							    }
						    }
					    },
				            "total": {
					            "type": "integer"
				            }
				    }
			    },
                            "date": {
                              "type":"date"
                            },
			    "fm_date":{
				    "type": "date"
			    },
                            "cpuslots":{
			            "type": "short"
                            },
                            "cpuslotsmax":{
			            "type": "short"
                            }
		    }
	    },
            "state-hist-summary": {
		            '_all': {'enabled': "false" },
                            "_parent": {
                                    "type": "run"
                            },
                            "properties": {
                                    "hmini": {
                                            "properties": {
                                                    "entries": {
                                                            "type" : "nested",
                                                            "properties": {
                                                                    "key": { "type": "short"},
                                                                    "count": {"type": "integer"}
                                                            }
                                                    },
                                                    "total": {
                                                            "type": "integer"
                                                    }
                                            }
                                    },
                                    "hmicro": {
                                            "properties": {
                                                    "entries": {
                                                            "type" : "nested",
                                                            "properties": {
                                                                    "key": {
                                                                            "type": "short"
                                                                    },
                                                                    "count": {
                                                                            "type": "integer"
                                                                    }
                                                            }
                                                    },
                                                    "total": {
                                                            "type": "integer"
                                                    }
                                            }
                                    },
                                    "hmacro": {
                                            "properties": {
                                                    "entries": {
                                                            "type" : "nested",
                                                            "properties": {
                                                                    "key": {
                                                                            "type": "short"
                                                                    },
                                                                    "count": {
                                                                            "type": "integer"
                                                                    }
                                                            }
                                                    },
                                                    "total": {
                                                        "type": "integer"
                                                    }
                                            }
                                    },
                                    "date": {
                                      "type":"date"
                                    },
				    "fm_date":{
				       "type": "date"
				    },
                                    "cpuslots":{
				       "type": "short"
                                    },
                                    "cpuslotsmax":{
				       "type": "short"
                                    }

			    }
	    }
#           ,
#           "transfer" : {
#             "_all" : {
#              "enabled" : False
#             },
#             "properties" : {
#               "fm_date" : {
#                 "type" : "date",
#               },
#               "id" : {
#                 "type" : "string","index" : "not_analyzed"
#               },
#               "runNumber" : {
#                 "type": "integer"
#               },
#               "ls" : {
#                 "type":"integer"
#               },
#               "stream": {
#                 "type":"string",
#                 "index":"not_analyzed"
#               },
#               "host":{
#                 "type":"string",
#                 "index":"not_analyzed"
#               },
#               #tier0 stream flag (TODO)
#
#             }
#           }
}


central_boxinfo_mapping = {
          'boxinfo' : {
            'properties' : {
              'fm_date'       :{'type':'date'
              },
              'id'            :{'type':'string','index':'not_analyzed'},
              'host'          :{'type':'string',"index":"not_analyzed"},
              'appliance'     :{'type':'string',"index":"not_analyzed"},
              'instance'      :{'type':'string',"index":"not_analyzed"},
              'broken'        :{'type':'integer'},
              'broken_activeRun':{'type':'integer'},
              'used'          :{'type':'integer'},
              'used_activeRun'  :{'type':'integer'},
              'idles'         :{'type':'integer'},
              'quarantined'   :{'type':'integer'},
              'cloud'         :{'type':'integer'},
              'usedDataDir'   :{'type':'integer'},
              'totalDataDir'  :{'type':'integer'},
              'usedRamdisk'   :{'type':'integer'},
              'totalRamdisk'  :{'type':'integer'},
              'usedOutput'    :{'type':'integer'},
              'totalOutput'   :{'type':'integer'},
              'activeRuns'    :{'type':'string','index':'not_analyzed'},
              'activeRunList'    :{'type':'integer'},
              'activeRunNumQueuedLS':{'type':'integer'},
              'activeRunCMSSWMaxLS':{'type':'integer'},
              "activeRunMaxLSOut":{'type':'integer'},
              "outputBandwidthMB":{'type':'integer'},
              "activeRunOutputMB":{'type':'integer'},
              "activeRunLSBWMB":{'type':'float'},
              "sysCPUFrac":{'type':'float'},
              "cpu_MHz_avg_real":{'type':'integer'},
              "dataNetIn":{"type":"float"},
              'activeRunStats'    :{
                  'type':'nested',
                  #"include_in_parent": True,
                  'properties': {
                      'run':      {'type': 'integer'},
                      'ongoing':  {'type': 'boolean'},
                      'totalRes': {'type': 'integer'},
                      'qRes':     {'type': 'integer'},
                      'errors':   {'type': 'integer'}
                      }
                  },
              'cloudState'    :{'type':'string',"index":"not_analyzed"},
              'detectedStaleHandle':{'type':'boolean'},
              'blacklist' : {'type':'string',"index":"not_analyzed"}
              #'activeRunsErrors':{'type':'string',"index":"not_analyzed"},#deprecated
              }
          },
          'resource_summary' : {
            '_all': {'enabled': "false" },
            'properties' : {
              'fm_date'       :{'type':'date'
              },
              'appliance' : {'type':'string',"index":"not_analyzed"},
              "activeFURun" : {"type" : "integer"},
              "activeRunCMSSWMaxLS" : {"type" : "integer"},
              "activeRunNumQueuedLS" :       { "type" : "integer" },
              "activeRunLSWithOutput":       { "type" : "integer" },
              "outputBandwidthMB":           { "type" : "integer"   },
              "activeRunOutputMB":           { "type" : "integer"   },
              "activeRunLSBWMB":             { "type" : "float"   },
              "active_resources" :           { "type" : "integer" },
              "active_resources_activeRun" : { "type" : "integer" },
              "broken" :                     { "type" : "integer" },
              "quarantined" :                { "type" : "integer" },
              "cloud" :                      { "type" : "integer" },
              "fu_workdir_used_quota" :      { "type" : "float" },
              "idle" :                       { "type" : "integer" },
              "pending_resources" :          { "type" : "integer" },
              "ramdisk_occupancy" :          { "type" : "float" },
              "stale_resources" :            { "type" : "integer" },
              "used" :                       { "type" : "integer" },
              "bu_stop_requests_flag":       { "type" : "boolean" },
              "fuSysCPUFrac":                {'type':'float'},
              "fuSysCPUMHz":                {'type':'integer'},
              "fuDataNetIn":                {"type":"float"},
              "resPerFU":                   {"type":"byte"}
              },
          },
          "fu-box-status" : {
            "_all": {"enabled": "false" },
            "properties": {
              "date":{"type":"date"},

              "cpu_name":{"type":"string","index":"not_analyzed"},
              "cpu_MHz_nominal":{"type":"integer"},
              "cpu_MHz_avg":{"type":"integer"},
              "cpu_MHz_avg_real":{"type":"integer"},
              "cpu_phys_cores":{"type":"integer"},
              "cpu_hyperthreads":{"type":"integer"},
              "cpu_usage_frac":{"type":"float"},
              "appliance":{"type":"string","index":"not_analyzed"},
              "host":{"type":"string","index":"not_analyzed"},
              "cloudState":{"type":"string","index":"not_analyzed"},
              "activeRunList":{"type":"integer"},
              "usedDisk":{"type":"integer"},
              "totalDisk":{"type":"integer"},
              "diskOccupancy":{"type":"float"},
              "usedDiskVar":{"type":"integer"},
              "totalDiskVar":{"type":"integer"},
              "diskVarOccupancy":{"type":"float"},
              "memTotal":{"type":"integer"},
              "memUsed":{"type":"integer"},
              "memUsedFrac":{"type":"float"},
              "dataNetIn":{"type":"float"},
              "dataNetOut":{"type":"float"}
            }
          }
}

central_hltdlogs_mapping = {
            'hltdlog' : {
		"_all": {"enabled": "false" },
                'properties' : {
                    'host'      : {'type' : 'string',"index":"not_analyzed"},
                    'type'      : {'type' : 'string',"index" : "not_analyzed"},
                    'severity'  : {'type' : 'string',"index" : "not_analyzed"},
                    'severityVal'  : {'type' : 'integer'},
                    'message'   : {'type' : 'string',"index" : "analyzed"},
                    'lexicalId' : {'type' : 'string',"index" : "not_analyzed"},
                    "run"       : {'type':'integer'},
                    'msgtime' : {
                            'type' : 'date',
                            'format':'YYYY-mm-dd HH:mm:ss||dd-MM-YYYY HH:mm:ss'
                    },
                    "date":{
                            "type":"date"
                    }
                }
            },

            "cmsswlog": {
		    "_all": {"enabled": "false" },
                    "properties": {
                            "host": {
                                    "type": "string",
                                    "index": "not_analyzed"
                            },
                            "pid": {
                                    "type": "integer"
                            },
                            "type": {
                                    "type": "string",
                                    "index": "not_analyzed"
                            },
                            "severity": {
                                    "type": "string",
                                    "index": "not_analyzed"
                            },
                            "severityVal": {
                                    "type": "integer"
                            },
                            "category": {
                                    "type": "string",
                                    "index": "not_analyzed"
                            },
                            "fwkState": {
                                    "type": "string",
                                    "index": "not_analyzed"
                            },

                            "module": {
                                    "type": "string",
                                    "index": "not_analyzed"
                            },
                            "moduleInstance": {
                                    "type": "string",
                                    "index": "not_analyzed"
                            },
                            "moduleCall": {
                                    "type": "string",
                                    "index": "not_analyzed"
                            },
                            "run" : {
                                    "type":"integer"
                            },
                            "lumi": {
                                    "type": "integer"
                            },
                            "eventInPrc": {
                                    "type": "long"
                            },
                            "message": {
                                    "type": "string",
                                    "index": "analyzed"
                            },
                            "lexicalId": {
                                    "type": "string",
                                    "index": "not_analyzed"
                            },
                            "msgtime": {
                                    "type": "date",
                                    "format": "YYYY-mm-dd HH:mm:ss||dd-MM-YYYY HH:mm:ss"
                            },
                            "msgtimezone": {
                                    "type": "string",
                                    "index": "not_analyzed"
                            },
                            "date": {
                                      "type":"date"
                            },

                    }
            }
}
