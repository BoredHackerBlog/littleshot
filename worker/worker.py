import hashlib
import re
import os
import json
from time import sleep

from playwright.sync_api import sync_playwright
from minio import Minio
import io
import pymongo

import yara
rules = yara.compile('./yara/rules.yar')

MINIO_SERVER = os.environ['MINIO_SERVER']
MINIO_ACCESS_KEY = os.environ['MINIO_ACCESS_KEY']
MINIO_SECRET_KEY = os.environ['MINIO_SECRET_KEY']
MINIO_BUCKET = os.environ['MINIO_BUCKET']

MONGODB_SERVER = os.environ['MONGODB_SERVER']
MONGODB_DATABASE = os.environ['MONGODB_DATABASE']
MONGODB_COLLECTION = os.environ['MONGODB_COLLECTION']

mongoclient = pymongo.MongoClient(MONGODB_SERVER)
mydb = mongoclient[MONGODB_DATABASE]
mycol = mydb[MONGODB_COLLECTION]

# this is the policy for setting the bucket as read-only for anonymous access
policy = {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":["*"]},"Action":["s3:GetBucketLocation","s3:ListBucket"],"Resource":[f"arn:aws:s3:::{MINIO_BUCKET}"]},{"Effect":"Allow","Principal":{"AWS":["*"]},"Action":["s3:GetObject"],"Resource":[f"arn:aws:s3:::{MINIO_BUCKET}/*"]}]}

minioclient = Minio(MINIO_SERVER,access_key=MINIO_ACCESS_KEY,secret_key=MINIO_SECRET_KEY,secure=False)
found = minioclient.bucket_exists(MINIO_BUCKET)
if not found:  #check if bucket exists, if it doesn't then create it and assign it the anonymous read-only policy
    minioclient.make_bucket(MINIO_BUCKET)
    minioclient.set_bucket_policy(MINIO_BUCKET, json.dumps(policy))

#this is the main screenshot task, it takes in taskid (generated by app) and url
def screenshot(taskid, url, private):
    data = {} #this is the data that will end up being stored in mongodb, you can add things to if you want such as additional processing

    data['private'] = private
    data['taskid'] = taskid
    data['url'] = url

    data['request'] = [] #contains all the requests
    data['response'] = [] #contains all the responses
    data['download'] = [] #contains downloada info

    with sync_playwright() as p:
        browser = p.chromium.launch(proxy={"server": "socks5://tor:9050"}) #launch chrome
        context = browser.new_context(ignore_https_errors=True) #new context, ignore https errors
        page = context.new_page() #new page

        def filter(route,request): #this drops requests containing certain things. i don't need people to look at file://, ip ranges or domains can be checked here too
            if "file://" in request.url:
                route.abort() #abort the request
            else:
                route.continue_() #allow the request

        #this handles requests, it adds request metadata to data['request']
        def request_handler(request):
            data['request'].append({"method":request.method, "url":request.url, "headers":request.headers, "post_data":request.post_data, "resource_type":request.resource_type})

        #this handles response, it adds response metadata to data['response']
        def response_handler(response):
            try:
                body_sha256 = hashlib.sha256(response.body()).hexdigest() #this hashes the response content
                body = True
                data['response'].append({"status":response.status, "url":response.url, "headers":response.headers, "body":body, "body_sha256":body_sha256})
            except:
                body = False
                data['response'].append({"status":response.status, "url":response.url, "headers":response.headers, "body":body})
            
        #this handles downloads
        def download_handler(download):
            data['download'].append({"url": download.url, "filename":download.suggested_filename})

        page.route("**/*", filter)

        page.on("request", request_handler)
        page.on("response", response_handler)
        page.on("download", download_handler)

        page.set_default_timeout(10000) #timeout set to 10 seconds

        try:
            page.goto(url) #go to the url
            sleep(3) # wait three seconds before taking a screenshot
            #png = page.screenshot(full_page=True) # take a full page screenshot
            png = page.screenshot() # take a screenshot, not full page
            data['title'] = page.title() # gets page title
            data['cookies'] = context.cookies() # gets cookies
            data['content'] = page.content() # gets page content/html
            data['content_sha256'] = hashlib.sha256(str.encode(data['content'])).hexdigest() # hash the content/html
            data['links'] = list(set(re.findall("href=[\"\'](.*?)[\"\']", data['content']))) # extract links, may not be accurate... https://www.kite.com/python/answers/how-to-get-href-links-from-urllib-urlopen-in-python
            data['yara_matches'] = str(rules.match(data=data['content']))
            object_name = taskid + ".png" # file name for minio file upload
            minioclient.put_object(MINIO_BUCKET,object_name,io.BytesIO(png),length=len(png),content_type="image/png") # upload the file to minio
        except Exception as e:
            data['error'] = str(e)

        page.close()
        context.close()
        browser.close()

    mycol.insert_one(data) # add data to mongodb

    return True