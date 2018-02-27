
#By Ria Bhatia
#Helpful sources: OpenCV tutorials
#For use by Microsoft and other parties to demo
#Azure Container Service, Azure Container Instances
#and the experimental ACI-connector

import sys
import numpy as np
import cv2
from PIL import Image
import glob
import os
import time
import requests
import time

from dbAzureBlob import DbAzureBlob

PICTURE_DIR = ""

start_time = time.time()                        # Start the timer

def detect(img, cascade, eyeCascade):                       # Figure out if the image has a face
    rects, eyes = [], []
    try:
        rects = cascade.detectMultiScale(img, scaleFactor=1.3, minNeighbors=4, minSize=(30, 30),flags=cv2.CASCADE_SCALE_IMAGE)
        print ("rects", rects)
        for (x,y,w,h) in rects: 
            roi_gray = gray[y:y+h, x:x+w]
            eyes = eyeCascade.detectMultiScale(roi_gray)
            print("eyes:", eyes)
            if len(eyes):
                return True                  # face found

    except Exception as e:
        print(e)

    return False                             # no face found


def getFilename(url):
    try:
        r = requests.get(url)
    except:
        print('url is false')
        return False

    if(r == None):
        print('Worker: No Request')
        return False

    if(r.status_code != 200):
        print('Worker: Status code not 200')
        return False

    return r.json()

#grab the filename request
def sendRes(url, filename, detected):
    try:
        r = requests.get(url + "/processed", params={
                "detected":detected,
                "filename":urllib.parse.quote(filename),
            })
    except:
        print("Failed to send response")

#make a request
jobserver_url = "http://" + os.getenv('IP_JOB_SERVER', "localhost")
print("JOB SERVER URL: ", jobserver_url)

counter = 0

dbHelper = DbAzureBlob()

while True:
    response = getFilename(jobserver_url)

    if(response == False):
        print("Failed to get response from jobserver")
        time.sleep(1)
        continue

    if(response['processed'] == 1):
        print("response is processed")
        time.sleep(1)

    filename = response['filename']
    realFilename = filename

    if(filename[:2] == "._"):
        filename = filename[2:]

    if(not dbHelper.getImageFromAzureBlob(filename, PICTURE_DIR + filename)):
        print("Failed to get image", filename)
        continue

    print("Got image: ", filename, " from blob")
    img = cv2.imread(PICTURE_DIR  + filename)
    os.remove(PICTURE_DIR  + filename)

    if img is None:
        print("Image is none!")
        continue

    cascade = cv2.CascadeClassifier('./haarcascade_frontalface_default.xml')
    eyeCascade = cv2.CascadeClassifier('./haarcascade_eye.xml')
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    face = detect(gray, cascade, eyeCascade)

    if face:
        print("face found in: ", realFilename)
        sendRes(jobserver_url,realFilename,"true")
    else:
        sendRes(jobserver_url,realFilename,"false")
