import cv2
import os
import numpy as np


def VideotoImage(Name):
    name = Name
    vidcap = cv2.VideoCapture('Input/Videos/%s.mp4' % name)
    success,image = vidcap.read()
    count = 0
    while success and count < 30:
        if not os.path.exists('Input\Videos\%s' % name):
            os.mkdir('Input\Videos\%s' % name)
        cv2.imwrite("Input/Videos/%s/frame%d.jpg" % (name,count), image)     # save frame as JPEG file
        success,image = vidcap.read()
        print('Read a new frame: ', success)
        count += 1
def ImagestoVideo(Name):
    img_array = []
    for filename in os.listdir(Name):
        img = cv2.imread(filename)
        height, width, layers = img.shape
        size = (width,height)
        img_array.append(img)


    out = cv2.VideoWriter('project.mp4',cv2.VideoWriter_fourcc(*'DIVX'), 15, size)

    for i in range(len(img_array)):
        out.write(img_array[i])
    out.release()
