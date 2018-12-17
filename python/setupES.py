#!/bin/env python
import sys,os
import six
from elasticsearch5 import Elasticsearch
from elasticsearch5.exceptions import TransportError

import simplejson as json
import socket
import logging

#compatibility (py3 unicode is str)
unicode = str if sys.version_info.major == 3 else unicode

def delete_template(es,name):
    es.indices.delete_template(name)

def load_template(name):
    filepath = os.path.join(os.path.dirname((os.path.realpath(__file__))),'../json',name+"Template.json")
    try:
        with open(filepath) as json_file:
            doc = json.load(json_file)
    except IOError as ex:
        #print ex
        doc = None
    except Exception as ex:
        #print ex
        doc = None
    return doc

def send_template(es,name,doc):
    es.indices.put_template(name,doc)

def create_template(es,name,label,subsystem,forceReplicas,forceShards,send=True):
    doc = load_template(label)
    doc["template"]="run*"+subsystem
    doc["order"]=1
    if forceReplicas>=0:
        doc['settings']['index']['number_of_replicas']=str(forceReplicas)
    if forceShards>=0:
        doc['settings']['index']['number_of_shards']=str(forceShards)
    if send:send_template(es,name,doc)
    return doc

#get rid of unicode elements
def convert(inp):
    if isinstance(inp, dict):
        return dict((convert(key), convert(value)) for key, value in six.iteritems(inp))
    elif isinstance(inp, list):
        return [convert(element) for element in inp]
    elif isinstance(inp, unicode):
        return inp.encode('utf-8')
    else:
        return inp

def printout(msg,usePrint,haveLog):
    if usePrint:
        print(msg)
    elif haveLog:
        logging.info(msg)


def setupES(es_server_url='http://localhost:9200',deleteOld=1,doPrint=False,overrideTests=False, forceReplicas=-1, forceShards=-1, create_index_name=None,subsystem="cdaq"):

    #ip_url=getURLwithIP(es_server_url)
    es = Elasticsearch(es_server_url,timeout=5) #TODO: timeout is invalid parameter, fix this!

    #list_template
    templateList = es.indices.get_template()

    TEMPLATES = ["runappliance_"+subsystem]
    loaddoc = None
    for template_name in TEMPLATES:
        template_label = template_name.split('_')[0]
        if template_name not in templateList:
            printout(template_name + " template not present. It will be created. ",doPrint,False)
            loaddoc = create_template(es,template_name,template_label,subsystem,forceReplicas,forceShards)
        else:
            loaddoc = create_template(es,None,template_label,subsystem,forceReplicas,forceShards,send=False)
            norm_name = convert(templateList[template_name])
            if deleteOld==0:
                printout(template_name+" already exists. Add 'replace' parameter to update if different, or forceupdate to always  update.",doPrint,False)
            else:
                printout(template_name+" already exists.",doPrint,False)
                if loaddoc!=None:
                    mappingSame =  norm_name['mappings']==loaddoc['mappings']
                    #settingSame = norm_name['settings']==loaddoc['settings']
                    settingsSame=True
                    #convert to int before comparison
                    if int(norm_name['settings']['index']['number_of_replicas'])!=int(loaddoc['settings']['index']['number_of_replicas']):
                        settingsSame=False
                    if int(norm_name['settings']['index']['number_of_shards'])!=int(loaddoc['settings']['index']['number_of_shards']):
                        settingsSame=False
                    #add more here if other settings need to be added
                    if 'translog' not in norm_name['settings']['index'] or norm_name['settings']['index']['translog']!=loaddoc['settings']['index']['translog']:
                        settingsSame=False
                    #currently analyzer settings are not verified

                    if not (mappingSame and settingsSame) or deleteOld>1:
                        #test is override
                        if overrideTests==False:
                            try:
                                if norm_name['settings']['test']==True:
                                    printout("Template test setting found, skipping update...",doPrint,True)
                                    break
                            except:pass
                        printout("Updating "+template_name+" ES template",doPrint,True)
                        create_template(es,template_name,template_label,subsystem,forceReplicas,forceShards)
                    else:
                        printout('runappliance ES template is up to date',doPrint,True)

    #create index
    if create_index_name:
        if loaddoc:
            try:
                c_res = es.indices.create(create_index_name, body = loaddoc)
                if c_res!={'acknowledged':True}:
                    printout("Result of index " + create_index_name + " create request: " + str(c_res),doPrint,True )
            except TransportError as ex:
                if ex[1]=='index_already_exists_exception':
                    #this is for index pre-creator
                    printout("Attempting to intialize already existing index "+create_index_name,doPrint,True)
                    try:
                        doc_resp = es.cat.indices(index=create_index_name,params={'h':'status'})
                        #doc_resp = es.cat.indices(index=create_index_name,'h'='status')
                        if doc_resp.strip('\n')=='close':
                            printout("Index "+create_index_name+ " is already closed! Index will be reopened",doPrint,True)
                            c_res = es.indices.open(create_index_name)
                    except TransportError as ex:
                        printout("setupES got TransportError trying to open/close index: "+str(ex),doPrint,True)
                    except Exception as ex:
                        printout("setupEs got Exception getting index open/closed: "+str(ex),doPrint,True)
            except Exception as ex:
                #if type(ex)==RemoteTransportException: print "a",type(ex)
                printout("Index not created: "+str(ex),doPrint,True)
        else:
            printout("Not creating index without a template",doPrint,True)

if __name__ == '__main__':

    if len(sys.argv) < 3:
        print("Please provide an elasticsearch server url (e.g. http://es-local:9200) and subsystem (e.g. cdaq,dv)")
        sys.exit(1)

    replaceOption=0
    if len(sys.argv)>3:
        if "replace" in sys.argv[3]:
            replaceOption=1
        if "forcereplace" in sys.argv[3]:
            replaceOption=2

    setupES(es_server_url=sys.argv[1],deleteOld=replaceOption,doPrint=True,overrideTests=True,subsystem=sys.argv[2])
