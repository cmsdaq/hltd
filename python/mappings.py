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
	              'type':'keyword'
                    },
                    'CMSSW_arch':{
	              'type':'keyword'
                    }
                }
            },
            'microstatelegend' : {
		'_all': {'enabled': "false" },
                '_parent':{'type':'run'},
                'properties' : {
	            'id':{'type':'keyword'},
                    'names':{
                        'type':'keyword'
                        },
                    'stateNames':{
                        'type':'keyword','index':'no'
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
	            'id':{'type':'keyword'},
                    'names':{
                        'type':'keyword'
                        },
                    'stateNames':{
                        'type':'keyword','index':'no'
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
                        'type':'keyword','index':'no'
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
                        'type':'keyword'
                        },
                    'fm_date':{
                        'type':'date'
                        },
                    'id'            :{'type':'keyword'}
                    }
                },
            'eols' : {
                '_all': {'enabled': "false" },
                '_parent'    :{'type':'run'},
                'properties' : {
                    'fm_date'       :{'type':'date'
                    },
                    'id'            :{'type':'keyword'},
                    'ls'            :{'type':'integer'},
                    'NEvents'       :{'type':'integer'},
                    'NFiles'        :{'type':'integer'},
                    'TotalEvents'   :{'type':'integer'},
                    'NLostEvents'   :{'type':'integer'},
                    'NBytes'        :{'type':'long'},
                    'appliance'     :{'type':'keyword'}
                    }
                },
            'minimerge' : {
                '_all': {'enabled': "false" },
                'properties' : {
                    'fm_date'       :{'type':'date'
                    },
                    'id'            :{'type':'keyword'}, #run + appliance + stream + ls
                    'appliance'     :{'type':'keyword'}, #wrong mapping:not analyzed
                    'host'          :{'type':'keyword'},
                    'stream'        :{'type':'keyword'},
                    'ls'            :{'type':'integer'},
                    'processed'     :{'type':'integer'},
                    'accepted'      :{'type':'integer'},
                    'errorEvents'   :{'type':'integer'},
                    'size'          :{'type':'long'},
		    'eolField1'     :{'type':'integer'},
		    'eolField2'     :{'type':'integer'},
		    'fname'         :{'type':'keyword'},
		    'adler32'       :{'type':'long'},
                    'runNumber'     :{'type':'integer'}
                    }
                },
            'macromerge' : {
                '_all': {'enabled': "false" },
                'properties' : {
                    'fm_date'       :{'type':'date'
                    },
                    'id'            :{'type':'keyword'}, #run + appliance + stream + ls
                    'appliance'     :{'type':'keyword'},
                    'host'          :{'type':'keyword'},
                    'stream'        :{'type':'keyword'},
                    'ls'            :{'type':'integer'},
                    'processed'     :{'type':'integer'},
                    'accepted'      :{'type':'integer'},
                    'errorEvents'   :{'type':'integer'},
                    'size'          :{'type':'long'},
		    'eolField1'     :{'type':'integer'},
		    'eolField2'     :{'type':'integer'},
		    'fname'         :{'type':'keyword'},
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
                                    "type": "keyword"
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
	    },

      "transfer" : {
		      "_all" : {
			      "enabled" : False
			      },
		      "properties" : {
			      "accepted" : {
				      "type" : "integer"
				      },
			      "appliance" : {
				      "type" : "keyword"
				      },
			      "endTime" : {
				      "type" : "date"
				      },
			      "eolField1" : {
				      "type" : "integer"
				      },
			      "eolField2" : {
				      "type" : "integer"
				      },
			      "errorEvents" : {
				      "type" : "integer"
				      },
			      "fm_date" : {
				      "type" : "date"
				      },
			      "fname" : {
				      "type" : "keyword"
				      },
			      "host" : {
				      "type" : "keyword"
				      },
			      "ls" : {
				      "type" : "integer"
				      },
			      "processed" : {
				      "type" : "integer"
				      },
			      "runNumber" : {
				      "type" : "integer"
				      },
			      "size" : {
				      "type" : "long"
				      },
			      "startTime" : {
				      "type" : "date"
				      },
			      "status" : {
				      "type" : "integer"
				      },
			      "stream" : {
				      "type" : "keyword"
				      },
			      "type" : {
				      "type" : "keyword"
				      }
			      }
    }
}


central_boxinfo_mapping = {
          'boxinfo' : {
            'properties' : {
              'fm_date'       :{'type':'date'
              },
              'id'            :{'type':'keyword'},
              'host'          :{'type':'keyword'},
              'appliance'     :{'type':'keyword'},
              'instance'      :{'type':'keyword'},
              'broken'        :{'type':'short'},
              'broken_activeRun':{'type':'short'},
              'used'          :{'type':'short'},
              'used_activeRun'  :{'type':'short'},
              'idles'         :{'type':'short'},
              'quarantined'   :{'type':'short'},
              'cloud'         :{'type':'short'},
              'usedDataDir'   :{'type':'integer'},
              'totalDataDir'  :{'type':'integer'},
              'usedRamdisk'   :{'type':'integer'},
              'totalRamdisk'  :{'type':'integer'},
              'usedOutput'    :{'type':'integer'},
              'totalOutput'   :{'type':'integer'},
              'activeRuns'    :{'type':'keyword'},
              'activeRunList'    :{'type':'integer'},
              'activeRunNumQueuedLS':{'type':'integer'},
              'activeRunCMSSWMaxLS':{'type':'integer'},
              "activeRunMaxLSOut":{'type':'integer'},
              "outputBandwidthMB":{'type':'float'},
              "activeRunOutputMB":{'type':'float'},
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
              'cloudState'    :{'type':'keyword'},
              'detectedStaleHandle':{'type':'boolean'},
              'blacklist' : {'type':'keyword'},
              'cpuName' : {'type':'keyword'}
              #'activeRunsErrors':{'type':'keyword'},#deprecated
              }
          },
          'resource_summary' : {
            '_all': {'enabled': "false" },
            'properties' : {
              "fm_date" :                    {"type":"date"},
              "appliance" :                  {"type":"keyword"},
              "activeFURun" :                {"type" : "integer"},
              "activeRunCMSSWMaxLS" :        {"type" : "integer"},
              "activeRunNumQueuedLS" :       { "type" : "integer" },
              "activeRunLSWithOutput":       { "type" : "integer" },
              "outputBandwidthMB":           { "type" : "float"   },
              "activeRunOutputMB":           { "type" : "float"   },
              "activeRunLSBWMB":             { "type" : "float"   },
              "active_resources" :           { "type" : "short" },
              "active_resources_activeRun" : { "type" : "short" },
              "idle" :                       { "type" : "short" },
              "used" :                       { "type" : "short" },
              "broken" :                     { "type" : "short" },
              "quarantined" :                { "type" : "short" },
              "cloud" :                      { "type" : "short" },
              "pending_resources" :          { "type" : "short" },
              "stale_resources" :            { "type" : "short" },
              "ramdisk_occupancy" :          { "type" : "float" },
              "fu_workdir_used_quota" :      { "type" : "float" },
              "fuDiskspaceAlarm" :           { "type" : "boolean" },
              "bu_stop_requests_flag":       { "type" : "boolean" },
              "fuSysCPUFrac":                {'type':'float'},
              "fuSysCPUMHz":                 {'type':'short'},
              "fuDataNetIn":                 {"type":"float"},
              "resPerFU":                    {"type":"byte"},
              "fuCPUName":                   {"type":"keyword"},
              "buCPUName":                   {"type":"keyword"}
              }
          },
          "fu-box-status" : {
            "_all": {"enabled": "false" },
            "properties": {
              "date":{"type":"date"},
              "cpu_name":{"type":"keyword"},
              "cpu_MHz_nominal":{"type":"integer"},
              "cpu_MHz_avg":{"type":"integer"},
              "cpu_MHz_avg_real":{"type":"integer"},
              "cpu_phys_cores":{"type":"integer"},
              "cpu_hyperthreads":{"type":"integer"},
              "cpu_usage_frac":{"type":"float"},
              "appliance":{"type":"keyword"},
              "host":{"type":"keyword"},
              "cloudState":{"type":"keyword"},
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
                    'host'      : {'type' : 'keyword'},
                    'type'      : {'type' : 'integer'},
                    'doctype'   : {'type' : 'keyword'},
                    'severity'  : {'type' : 'keyword'},
                    'severityVal'  : {'type' : 'integer'},
                    'message'   : {'type' : 'text'},
                    'lexicalId' : {'type' : 'keyword'},
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
                                    "type": "keyword"
                            },
                            "pid": {
                                    "type": "integer"
                            },
                            "type": {
                                    "type": "integer"
                            },
                            "doctype": {
                                    "type" : "keyword"
                            },
                            "severity": {
                                    "type": "keyword"
                            },
                            "severityVal": {
                                    "type": "integer"
                            },
                            "category": {
                                    "type": "keyword"
                            },
                            "fwkState": {
                                    "type": "keyword"
                            },

                            "module": {
                                    "type": "keyword"
                            },
                            "moduleInstance": {
                                    "type": "keyword"
                            },
                            "moduleCall": {
                                    "type": "keyword"
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
                                    "type": "text"
                            },
                            "lexicalId": {
                                    "type": "keyword"
                            },
                            "msgtime": {
                                    "type": "date",
                                    "format": "YYYY-mm-dd HH:mm:ss||dd-MM-YYYY HH:mm:ss"
                            },
                            "msgtimezone": {
                                    "type": "keyword"
                            },
                            "date": {
                                      "type":"date"
                            }

                    }
            }
}
