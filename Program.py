# python drowniness_yawn.py --webcam webcam_index

from scipy.spatial import distance as dist
from imutils.video import VideoStream
from imutils import face_utils
from threading import Thread
import numpy as np
import argparse
import Jetson.GPIO as GPIO
import imutils
import time
import dlib
import cv2
import os

font = cv2.FONT_ITALIC

GPIO.setmode(GPIO.BOARD)
channel = 15
GPIO.setup(channel,GPIO.OUT)

def rescale_frame(frame, percent=75):
    width = int(frame.shape[1] * percent / 100)
    height = int(frame.shape[0] * percent / 100)
    dim = (width, height)
    return cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)


def alarm(msg):
    global alarm_status
    global alarm_status2
    global saying

    while alarm_status:
        print('call')
        s = 'espeak "' + msg + '"'
        os.system(s)

    if alarm_status2:
        print('call')
        saying = True
        s = 'espeak "' + msg + '"'
        os.system(s)
        saying = False


def eye_aspect_ratio(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])

    C = dist.euclidean(eye[0], eye[3])

    ear = (A + B) / (2.0 * C)

    return ear


def final_ear(shape):
    (lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
    (rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

    leftEye = shape[lStart:lEnd]
    rightEye = shape[rStart:rEnd]

    leftEAR = eye_aspect_ratio(leftEye)
    rightEAR = eye_aspect_ratio(rightEye)

    ear = (leftEAR + rightEAR) / 2.0
    return (ear, leftEye, rightEye)


ap = argparse.ArgumentParser()
ap.add_argument("-w", "--webcam", type=int, default=0,
                help="index of webcam on system")
args = vars(ap.parse_args())

EYE_AR_THRESH = 0.26
EYE_AR_CONSEC_FRAMES = 10
YAWN_THRESH = 35
alarm_status = False
alarm_status2 = False
saying = False
COUNTER = 0

print("-> Loading the predictor and detector...")
detector = dlib.get_frontal_face_detector()
# detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")    #Faster but less accurate
predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')

print("-> Starting Video Stream")
vs = VideoStream(src=args["webcam"]).start()

# vs= VideoStream(usePiCamera=True).start()       //For Raspberry Pi
time.sleep(1.0)
while True:
    frame = vs.read()
    frame = imutils.resize(frame, width=450)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rects = detector(gray, 0)
    # rects = detector.detectMultiScale(gray, scaleFactor=1.1,
    # minNeighbors=5, minSize=(30, 30),
    # flags=cv2.CASCADE_SCALE_IMAGE)
    cv2.putText(frame, 'Focust Assistant', (10, 40), font, 1, (255, 51, 51), 4)
    # for rect in rects:
    '''if (len(faces) == 0):
        COUNTER1 += 4
        if COUNTER1 >= 120:
            cv2.putText(frame, "Warning!!", (20, 200),
                        font, 1, (0, 0, 255), 4)
            cv2.putText(frame, "Pekerja tidak terdeteksi", (20, 400),
                        font, 1, (0, 0, 255), 4)

    else:
        COUNTER1 = 0'''
    for rect in rects:
        #rect = dlib.rectangle(int(x), int(y), int(x + w), int(y + h))

        shape = predictor(gray, rect)
        shape = face_utils.shape_to_np(shape)

        eye = final_ear(shape)
        ear = eye[0]
        leftEye = eye[1]
        rightEye = eye[2]

        leftEyeHull = cv2.convexHull(leftEye)
        rightEyeHull = cv2.convexHull(rightEye)
        cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)
        cv2.putText(frame, "ear rasio = {q}".format(q=ear), (10,100),font,1, (0,255,0), 1)
        #kolom baris
        if ear < EYE_AR_THRESH:
            COUNTER += 1
            if COUNTER >= EYE_AR_CONSEC_FRAMES:
                if alarm_status == False:
                    alarm_status = True
                    t = Thread(target=alarm, args=('WAKE UP',))
                    t.deamon = True
                    t.start()
                cv2.putText(frame, "Warning!!", (10, 200),
                            font, 1, (0, 0, 255), 4)
                cv2.putText(frame, "Pekerja Terdistraksi", (10, 400),
                            font, 1, (0, 0, 255), 4)
                GPIO.output(channel,GPIO.HIGH)

        else:
            COUNTER = 0
            alarm_status = False
            GPIO.output(channel, GPIO.LOW)

    frame100 = rescale_frame(frame, percent=300)
    cv2.imshow('frame100', frame100)
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

cv2.destroyAllWindows()
vs.stop()
