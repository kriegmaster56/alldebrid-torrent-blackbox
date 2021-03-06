#!/usr/bin/env python3

import configparser
# TODO argparser, custom config
import argparse
import requests
import os
import json
import shutil
import logging
from time import sleep
logger = None


_agent = "BlackHole"
_MAX_TORRENT_COUNT = 5

api = None
config = None
monitor_path = None
download_path = None
crawl_path = None
parser = None 
args = None 

torrent_list = []
payload = {}

api_url = 'http://api.alldebrid.com/v4/'

def getConfig():
    global api, config, monitor_path, download_path, crawl_path, torrent_list, logger 

    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.info("Started monitoring...")

    config = configparser.ConfigParser()
    config.read(args.config)
    
    download_path = "/etc/download/"
    # TODO cleanup this part 
    if args.api != None:
        api = args.api
    elif 'api'in config['Config'].keys() : 
        api = config['Config']['API']
    else: 
        raise AttributeError("No API key.")

    monitor_path = "/etc/monit/"

    crawl_path = "./crawl/"

    logger.info("Monitoring torrents under: %s ; Output crawljob directory: %s " % ( monitor_path, crawl_path ) )

    if os.path.isfile("torrent_list.txt"):
        f = open('torrent_list.txt', 'r')
        torrent_list = list(map(lambda x: int(x), f.readlines()))
    payload['apikey'] = api
    payload['agent'] = _agent

def createFolders():
    if not os.path.isdir(monitor_path):
        os.mkdir(monitor_path)
    if not os.path.isdir(download_path):
        os.mkdir(download_path)
    if not os.path.isdir(crawl_path):
        os.mkdir(crawl_path)
    if not os.path.isdir(crawl_path + '/added/'):
        os.mkdir(crawl_path + '/added/')

def testAPI():
    r = requests.get(api_url + 'user', payload)
    return r.json()['status'] == 'success'

def poll():
    toUpload = {}
    # TODO: upload magnet links too 
    magnetLinks = {}
    magnetFiles = []

    i = 0
    j = 0

    for f in os.listdir(monitor_path):
        # TODO: Get active torrents and add as many as allowed
        # open items
        if f.endswith(".torrent") and i < _MAX_TORRENT_COUNT:
            # https://2.python-requests.org/en/master/user/quickstart/#more-complicated-post-requests
            # If you want, you can send strings to be received as files:

            # Apparently it's important to upload as an array with index
            toUpload['files[%d]' % i] = (
                f,  open(monitor_path + f, 'rb'), 'application/x-bittorrent')

            logger.info("Added torrent: %s to AllDebrid server" % ( f ))
            i += 1

        if f.endswith(".magnet") and i < _MAX_TORRENT_COUNT:
            magnetLinks['magnets[%d]' % j] = open(monitor_path + f, 'r').read()
            logger.info("Added torrent: %s to AllDebrid server" % ( f ))
            magnetFiles.append(f)
            j += 1

    if ( len(toUpload) > 0 ):
        postResponse = requests.post(
            api_url + 'magnet/upload/file', params=payload, files=toUpload)
        # Close items
        for toClose in toUpload.values():
            toClose[1].close()
        postResponse.raise_for_status()
    
        response = postResponse.json()
        if response['status'] == 'success' :
            # Extend torrent list by added torrents
            torrent_list.extend(
                map(lambda x: x['id'],  response['data']['files']))
            for file in response['data']['files']:
                filename = file['file']
                if os.path.isfile(monitor_path + filename):
                    try:
                        shutil.move(monitor_path + filename,
                                    crawl_path + "added/" + filename)
                    except PermissionError as e:
                        logger.error(e)
                        pass
               
    if ( len(magnetLinks) > 0 ):

        new_payload = payload.copy()
        new_payload.update(magnetLinks)

        getResponse = requests.get(
            api_url + 'magnet/upload', params=new_payload)
            # 'https://postman-echo.com/post', params=payload, files=magnetLinks)

        # Close items
        getResponse.raise_for_status()
        response = getResponse.json()

        # Extend torrent_list
        torrent_list.extend(
                    map(lambda x: x['id'],  response['data']['magnets']))

        for file in magnetFiles:
            if os.path.isfile(monitor_path + file):
                try:
                    shutil.move(monitor_path + file,
                                crawl_path + "added/" + file)
                except PermissionError as e:
                    logger.error(e)
                    pass

    # Move magnet files to added folder 
    # Move .torrent files to added folder
    
    # Get count
    r = requests.get(api_url + 'magnet/status', payload)
    r.raise_for_status()
    response = r.json()

    if response['status'] == 'success':
        parseMagnets(response['data']['magnets'])

    # update torrent_list
    with open('torrent_list.txt', 'w') as f:
        f.writelines(map(lambda x: str(x) + "\n", torrent_list))


def parseMagnets(magnetList: list):
    count = 0

    for magnet in magnetList:
        code = magnet['statusCode']

        if code > 0 and code < 1:
            count += 1

        # Ready to download
        elif code == 4 and magnet['id'] in torrent_list:
            downloadFile(magnet, download_path)
    return count

def downloadFile(magnet: dict,download_path):
  payload['link'] = "%s" % magnet['links'][0]['link']
  local_filename = "%s"  % magnet['filename']
  
  r = requests.get(api_url + 'link/unlock', payload)
  r.raise_for_status()
  reponse = r.json()
  dowload_url = "%s"  % reponse['data']['link']
  
  logger.info('Download of %s from AllDebrid tasks'  % magnet['filename'])

  with requests.get(dowload_url, payload, stream=True) as r:
     r.raise_for_status()
     with open(download_path + '/' + local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)
  logger.info('Download of %s finished'  % magnet['filename'])
  # Delete from list
  new_payload = payload.copy() 
  new_payload['id'] = magnet['id']
  r = requests.get(api_url + "magnet/delete", new_payload ) 

  r.raise_for_status()
  if r.json()['status'] == 'success': 
      logger.info('Deleted torrent: %s from AllDebrid tasks'  % magnet['filename'])
  else:
      logger.warn('Could not delete torrent: %s from AllDebrid server. %s' % ( magnet['filename'], r.json() )  )

def start():
    getConfig()
    createFolders()
    if not testAPI():
        raise Exception("API key seems to be wrong")
    while True: 
        try: 
            poll()
        except Exception as e:
            logger.error(repr(e))
        sleep(10)

def setupArgs():
    global parser, args
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Path of the config.ini file", default="config.ini")
    parser.add_argument("--api", help="API Token for alldebrid")
    args = parser.parse_args()

    start()

setupArgs()
