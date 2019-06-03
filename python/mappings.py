central_es_settings_runindex = {
            'analysis':{
                'analyzer': {
                    'default': {
                        'type': 'keyword'
                    }
                }
            },
            'index':{
                'number_of_shards' : 8,
                'number_of_replicas' : 2,
                'codec' : 'best_compression',
                'translog':{'durability':'async','flush_threshold_size':'4g'},
                'mapper':{'dynamic':'false'}
            }
        }


central_es_settings_boxinfo = {
            'analysis':{
                'analyzer': {
                    'default': {
                        'type': 'keyword'
                    }
                }
            },
            'index':{
                'number_of_shards' : 8,
                'number_of_replicas' : 1,
                'codec' : 'best_compression',
                'translog':{'durability':'async','flush_threshold_size':'4g'},
                'mapper':{'dynamic':'false'}
            }
        }

central_es_settings_reshistory = central_es_settings_boxinfo

central_es_settings_hltlogs = {

            'analysis':{
                'analyzer': {
                    'prefix-test-analyzer': {
                        'type': 'custom',
                        'tokenizer': 'prefix-test-tokenizer'
                    }
                },
                'tokenizer': {
                    'prefix-test-tokenizer': {
                        'type': 'path_hierarchy',
                        'delimiter': ' '
                    }
                }
            },
            'index':{
                'number_of_shards' : 8,
                'number_of_replicas' : 1,
                'codec' : 'best_compression',
                'translog':{'durability':'async','flush_threshold_size':'4g'},
                'mapper':{'dynamic':'false'}
            }
        }


central_runindex_mapping = {
    'properties' : {
        'runRelation': {'type':'join','relations':{'run':['eols','stream-hist','stream-hist-appliance','state-hist','state-hist-summary','microstatelegend','inputstatelegend','pathlegend','stream_label']}},
        'runNumber':  {'type':'long'},
        'startTimeRC':{'type':'date'},
        'stopTimeRC': {'type':'date'},
        'startTime':  {'type':'date'},
        'endTime':    {'type':'date'},
        'completedTime' :  {'type':'date'},
        'activeBUs':       {'type':'integer'},
        'totalBUs':        {'type':'integer'},
        'rawDataSeenByHLT':{'type':'boolean'},
        'CMSSW_version':   {'type':'keyword'},
        'CMSSW_arch':      {'type':'keyword'},
        'HLT_menu':        {'type':'keyword'},

        'id':         {'type':'keyword'},
        'names':      {'type':'keyword'},
        'stateNames': {'type':'keyword','index':'false'},
        'reserved':   {'type':'integer'},
        'special':    {'type':'integer'},
        'output':     {'type':'integer'},
        'fm_date':    {'type':'date'},

        'stream':       {'type':'keyword'},
        'ls'            :{'type':'integer'},
        'NEvents'       :{'type':'integer'},
        'NFiles'        :{'type':'integer'},
        'TotalEvents'   :{'type':'integer'},
        'NLostEvents'   :{'type':'integer'},
        'NBytes'        :{'type':'long'},
        'appliance'     :{'type':'keyword'},

        'host'          :{'type':'keyword'},
        'processed'     :{'type':'integer'},
        'accepted'      :{'type':'integer'},
        'errorEvents'   :{'type':'integer'},
        'size'          :{'type':'long'},
        'eolField1'     :{'type':'integer'},
        'eolField2'     :{'type':'integer'},
        'fname'         :{'type':'keyword'},
        'adler32'       :{'type':'long'},

        'status' : {          'type' : 'integer'        },
        'type' : {          'type' : 'keyword'        },
        'in': {          'type': 'float'        },
        'out': {          'type': 'float'        },
        'err': {          'type': 'float'        },
        'filesize': {          'type': 'float'        },
        'completion':{          'type': 'double'        },
        'date':{          'type': 'date'        },
        'hminiv': {
          'properties': {
            'entries': {
              'properties': {
                'key': {                  'type': 'short'                },
                'count': {                  'type': 'integer'                }
              }
            },
            'total': {              'type': 'integer'            }
          }
        },
        'hmicrov': {
          'properties': {
            'entries': {
              'properties': {
                'key': {                  'type': 'short'                },
                'count': {                  'type': 'integer'                }
              }
            },
            'total': {              'type': 'integer'            }
          }
        },
        'hmacrov': {
          'properties': {
            'entries': {
              'properties': {
                'key': {                  'type': 'short'                },
                'count': {                  'type': 'integer'                }
              }
            },
            'total': {              'type': 'integer'            }
          }
        },
        'cpuslots':{          'type': 'short'        },
        'cpuslotsmax':{          'type': 'short'        },
        'hmini': {
          'properties': {
            'entries': {
              'type' : 'nested',
              'properties': {
                'key': { 'type': 'short'},
                'count': {'type': 'integer'}
              }
            },
            'total': {              'type': 'integer'            }
          }
        },
        'hmicro': {
          'properties': {
            'entries': {
              'type' : 'nested',
              'properties': {
                'key': {                  'type': 'short'                },
                'count': {                  'type': 'integer'                }
              }
            },
            'total': {              'type': 'integer'            }
          }
        },
        'hmacro': {
          'properties': {
            'entries': {
              'type' : 'nested',
              'properties': {
                'key': {                  'type': 'short'                },
                'count': {                  'type': 'integer'                }
              }
            },
            'total': {              'type': 'integer'            }
          }
        }
      }

}


central_boxinfo_mapping = {
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
      'activeRunMaxLSOut':{'type':'integer'},
      'outputBandwidthMB':{'type':'float'},
      'activeRunOutputMB':{'type':'float'},
      'activeRunLSBWMB':{'type':'float'},
      'sysCPUFrac':{'type':'float'},
      'cpu_MHz_avg_real':{'type':'integer'},
      'bu_percpu_MHz_real': {'type':'integer'},
      'bu_cpu_loadfactor':  {'type':'float','index':'false'},
      'bu_percpu_c1_frac' : {'type':'float','index':'false'},
      'bu_percpu_c3_frac' : {'type':'float','index':'false'},
      'bu_percpu_c6_frac' : {'type':'float','index':'false'},
      'bu_percpu_c7_frac' : {'type':'float','index':'false'},
      'bu_percpu_s0_poll' : {'type':'float','index':'false'},
      'bu_percpu_s1_c1' : {'type':'float','index':'false'},
      'bu_percpu_s2_c1e' : {'type':'float','index':'false'},
      'bu_percpu_s3_c6' : {'type':'float','index':'false'},
      'dataNetIn':{'type':'float'},
      'activeRunStats'    :{
        'type':'nested',
        'properties': {
          'run':      {'type': 'integer'},
          'ongoing':  {'type': 'boolean'},
          'totalRes': {'type': 'integer'},
          'qRes':     {'type': 'integer'},
          'errors':   {'type': 'integer'},
          'errorsRes':   {'type': 'integer'}
        }
      },
      'cloudState'    :{'type':'keyword'},
      'detectedStaleHandle':{'type':'boolean'},
      'blacklist' : {'type':'keyword'},
      'cpuName' : {'type':'keyword'},
      'cpu_phys_cores':{'type':'integer'},
      'cpu_hyperthreads':{'type':'integer'},
      'activeFURun' :                {'type' : 'integer'},
      'activeRunLSWithOutput':       { 'type' : 'integer' },
      'activeRunHLTErr':             { 'type' : 'float'   },
      'active_resources' :           { 'type' : 'short' },
      'active_resources_activeRun' : { 'type' : 'short' },
      'active_resources_oldRuns' :   { 'type' : 'short' },
      'idle' :                       { 'type' : 'short' },
      'pending_resources' :          { 'type' : 'short' },
      'stale_resources' :            { 'type' : 'short' },
      'ramdisk_occupancy' :          { 'type' : 'float' },
      'fu_workdir_used_quota' :      { 'type' : 'float' },
      'fuDiskspaceAlarm' :           { 'type' : 'boolean' },
      'bu_stop_requests_flag':       { 'type' : 'boolean' },
      'fuSysCPUFrac':                {'type':'float'},
      'fuSysCPUMHz':                 {'type':'short'},
      'fuDataNetIn':                 {'type':'float'},
      'fuDataNetIn_perfu':           {'type':'float','index':'false'},
      'resPerFU':                    {'type':'byte'},
      'fuCPUName':                   {'type':'keyword'},
      'buCPUName':                   {'type':'keyword'},
      'activePhysCores':             {'type':'short'},
      'activeHTCores':               {'type':'short'},
      'fuMemFrac':                   {'type':'float'},
      'date':{'type':'date'},
      'cpu_name':{'type':'keyword'},
      'cpu_MHz_nominal':{'type':'integer'},
      'cpu_MHz_avg':{'type':'integer'},
      'cpu_usage_frac':{'type':'float'},
      'usedDisk':{'type':'integer'},
      'totalDisk':{'type':'integer'},
      'diskOccupancy':{'type':'float'},
      'usedDiskVar':{'type':'integer'},
      'totalDiskVar':{'type':'integer'},
      'diskVarOccupancy':{'type':'float'},
      'memTotal':{'type':'integer'},
      'memUsed':{'type':'integer'},
      'memUsedFrac':{'type':'float'},
      'dataNetOut':{'type':'float'}
    }
}

central_reshistory_mapping = central_boxinfo_mapping

central_hltdlogs_mapping = {
        'properties' : {
            'doc_type'  : {'type' : 'keyword'},

            'host'      : {'type' : 'keyword'},
            'type'      : {'type' : 'integer'},
            'doctype'   : {'type' : 'keyword'},
            'severity'  : {'type' : 'keyword'},
            'severityVal'  : {'type' : 'integer'},
            'message'   : {'type' : 'text'},
            'lexicalId' : {'type' : 'keyword'},
            'run'       : {'type':'integer'},
            'msgtime' : {
                'type' : 'date',
                'format':'YYYY-MM-dd HH:mm:ss||dd-MM-YYYY HH:mm:ss'
            },
            'date':{
                'type':'date'
            },
            'pid': {
                'type': 'integer'
            },
            'category': {
                'type': 'keyword'
            },
            'fwkState': {
                'type': 'keyword'
            },
            'module': {
                'type': 'keyword'
            },
            'moduleInstance': {
                'type': 'keyword'
            },
            'moduleCall': {
                'type': 'keyword'
            },
            'lumi': {
                'type': 'integer'
            },
            'eventInPrc': {
                'type': 'long'
            },
            'message': {
                'type': 'text'
            },
            'msgtimezone': {
                'type': 'keyword'
            }
        }
}
