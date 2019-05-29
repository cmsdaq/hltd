runappliance = {
  "index_patterns": "run*",

  "settings": {
    "analysis": {
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
    "index": {
      "number_of_shards": "2",
      "number_of_replicas": "1",
      "translog":{"durability":"async","flush_threshold_size":"4g"}
    }
  },
  "mappings": {
      "properties": {
        "doc_type": {
          "type": "keyword"
        },
        "macro": {
          "type": "integer"
        },
        "mini": {
          "type": "integer"
        },
        "micro": {
          "type": "integer"
        },
        "instate": {
          "type": "integer"
        },
        "tp": {
          "type": "double"
        },
        "lead": {
          "type": "double"
        },
        "nfiles": {
          "type": "integer"
        },
        "nevents": {
          "type": "integer"
        },
        "lockwaitUs": {
          "type": "double"
        },
        "lockcount": {
          "type": "integer"
        },
        "fm_date": {
          "type": "date"
        },
        "source": {
          "type": "keyword"
        },
        "mclass" : {
          "type": "keyword"
        },

        "miniv": {
          "properties":{
            "key":{"type":"integer","index":"false"},
            "value":{"type":"integer","index":"false"}
          }
        },
        "microv": {
          "properties":{
            "key":{"type":"integer","index":"false"},
            "value":{"type":"integer","index":"false"}
          }
        },
        "inputStats" : {
          "properties" : {
            "tp": {
              "type": "double",
              "index":"false",
              "doc_values":True
            },
            "lead": {
              "type": "double",
              "index":"false",
              "doc_values":True
            },
            "nfiles": {
              "type": "integer",
              "index":"false",
              "doc_values":True
            },
            "nevents": {
              "type": "integer",
              "index":"false",
              "doc_values":True
            },
            "lockwaitUs": {
              "type": "double",
              "index":"false",
              "doc_values":True
            },
            "lockcount": {
              "type": "integer",
              "index":"false",
              "doc_values":True
            },
            "instatev": {
              "properties":{
                "key":{"type":"integer","index":"false"},
                "value":{"type":"integer","index":"false"}
              }
            }
          }
        },
        "ls": {
          "type": "integer",
          "store": True
        },
        "host": {
          "type": "keyword"
        },
        "pid": {
          "type": "integer"
        },
        "tid": {
          "type": "integer"
        },
        "din": {
          "type": "integer",
          "index":"false",
          "doc_values":True
        },
        "dout": {
          "type": "integer",
          "index":"false",
          "doc_values":True
        },
        "lsn": {
          "type": "integer",
          "store": False,
          "doc_values":False
        },
        "streamn": {
          "type": "keyword",
          "store": False,
          "doc_values":True
        },
        "pidn": {
          "type": "integer",
          "store": False,
          "doc_values":True
        },
        "hostn": {
          "type": "keyword",
          "store": False,
          "doc_values":True
        },
        "appn": {
          "type": "keyword",
          "store": False,
          "doc_values":True
        },
        "fm_d": {
          "type": "date",
          "store":False,
          "doc_values":True,
          "format":"epoch_millis"
        },
        "appliance": {
          "type": "keyword"
        },
        "data": {
          "properties": {
            "out": {
              "type": "integer"
            },
            "size": {
              "type" : "long"
            },
            "in": {
              "type": "integer"
            },
            "errorEvents": {
              "type": "integer"
            },
            "hltErrorEvents": {
              "type": "integer"
            },
            "returnCodeMask": {
              "type": "keyword"
            },
            "fileSize": {
              "type": "long"
            },
            "fileAdler32": {
              "type": "long"
            },
            "TransferDestination": {
              "type": "keyword"
            },
            "MergeType": {
              "type": "keyword"
            },
            "InputFiles": {
              "type": "keyword"
            }
          }
        },
        "index": {
          "type": "integer"
        },
        "stream": {
          "type": "keyword"
        },
        "appliance": {
          "type": "keyword"
        },
        "MergingTime":{
          "type": "float"
        },
        "MergingTimePerFile":{
          "type": "float"
        },

        "numQueuedLS": {
          "type": "integer"
        },
        "maxQueuedLS": {
          "type": "integer"
        },
        "numReadFromQueueLS": {
          "type": "integer"
        },
        "maxClosedLS": {
          "type": "integer"
        },
        "numReadOpenLS": {
          "type": "integer"
        },
        "CMSSWMaxLS": {
          "type": "integer"
        },
        "doctype": {
          "type": "keyword"
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
        "run": {
          "type": "integer"
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
          "format": "YYYY-MM-dd HH:mm:ss"
        },
        "msgtimezone": {
          "type": "keyword"
        },
        "date" : {
          "type": "date"
        }
      }
  }
}

