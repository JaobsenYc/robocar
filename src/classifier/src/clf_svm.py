#!/usr/bin/python
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
from std_msgs.msg import Int8, Time

import numpy as np
import cv2
from sklearn import svm
from scipy.ndimage.measurements import label
import imagefunctions
from tracker import Tracker
import pickle
#import random
import time

###########################################################3
# sliding window parameters
imgsize = (128,96)
windowsize = (50,50)
slidestep = (5,5) # number of pixels to slide window
min_red_pixels = 20 # min red pixel to process window
nhistory=1 # tracker buffer

class SVMCLF():
    def __init__(self):
        rospy.init_node('classifier', anonymous=True)
        fn_model = rospy.get_param('~svmModelFile')
        fn_params = rospy.get_param('~svmParamsFile')
        self.clf = pickle.load(open(fn_model, 'rb'))
        svmparams = pickle.load(open(fn_params, 'rb')) #pickle.load(f2)
        self.fmean = svmparams['fmean']
        self.fstd = svmparams['fstd']
        self.tracker = Tracker(nhistory)
        rospy.Subscriber("driver_node/time", Time, self.time_callback, queue_size=1)
        rospy.Subscriber("camera/image", Image, self.callback, queue_size=1)
#        self.bridge = CvBridge()
        self.pub = rospy.Publisher('driver_node/drivestate', Int8, queue_size=1)

        self.drive_state = 0

#        self.imgsvm_pub = rospy.Publisher('camera/imgsvm', Image, queue_size=1)

        self.loop()

    def time_callback(self,rostime):
        print "Data freshness: " + str(time.time() - rostime.data.secs)
		
    def callback(self,rosimg):
        print 'callback ' + str(rospy.get_rostime().secs - rosimg.header.stamp.secs)
        start_time = time.time()
        # ---- process frame here ---
        #dec,draw_img = self.processOneFrame(self.bridge.imgmsg_to_cv2(rosimg))
        dec,draw_img = self.processOneFrame(CvBridge().imgmsg_to_cv2(rosimg))
        print str(dec) + " (" + str(time.time() - start_time) + " sec)"
 #       self.imgsvm_pub.publish(self.bridge.cv2_to_imgmsg(draw_img, "bgr8"))
        self.drive_state = dec
        self.pub.publish(self.drive_state)

    def loop(self):
        dt = 0.1
        rate = rospy.Rate(1/dt)
        while not rospy.is_shutdown():
            rate.sleep()

    def getFeatures(self,img):
        return [
            imagefunctions.num_corners(img),
            imagefunctions.num_edges(img),
            imagefunctions.num_red_pixels(img),
            imagefunctions.num_white_pixels(img),
            imagefunctions.abs_sobel_thresh(img, orient='y', sobel_kernel=3, thresh=(100, 200)),
            imagefunctions.mag_thresh(img, sobel_kernel=5, mag_thresh=(100, 180)),
            imagefunctions.dir_threshold(img, sobel_kernel=3, thresh=(np.pi/8, np.pi/4))
        ]

    def normalize_features(self,feature_vector,fmn,fsd):
        numDim = len(feature_vector)
        normFeatures = []
        normfeat = [None]*numDim
        for i in range(numDim):
            normfeat[i] = (feature_vector[i]-fmn[i])/fsd[i]
        normFeatures.append(normfeat)
        #transpose result
        res = np.array(normFeatures).T
        return res

    def search_windows(self,img, windows,framenum = 0):
        # preprocess frame
        img_prep = imagefunctions.preprocess_one_rgb(img[0:127][:])
        fvec=[]
        for window in windows:
            # extract test window from image
            test_img = img_prep[window[0][1]:window[1][1], window[0][0]:window[1][0]]
            # extract features
            feat = self.getFeatures(test_img)
            # normalize features
            normfeat = self.normalize_features(feat,self.fmean,self.fstd)
            # assemble batch
            testvec = np.asarray(normfeat).reshape(1,-1)
            fvec.append(testvec)

        # batch prediction
        rvec = self.clf.predict(np.array(fvec).squeeze())

        # list of positive stop sign detection windows
        stop_indices = [i for i, x in enumerate(rvec) if x==1]
        stop_windows = [windows[i] for i in stop_indices]

        # list of positive warn sign detection windows
        warn_indices = [i for i, x in enumerate(rvec) if x==2]
        warn_windows = [windows[i] for i in warn_indices]

        print str(len(stop_windows)) + ", " + str(len(warn_windows))
        # return positve detection windows
        return stop_windows, warn_windows

    def draw_labeled_bboxes(self,img, labels, boxcolor):
        # Iterate through all detected cars
        for item_number in range(1, labels[1]+1):
            # Find pixels with each item_number label value
            nonzero = (labels[0] == item_number).nonzero()
            # Identify x and y values of those pixels
            nonzeroy = np.array(nonzero[0])
            nonzerox = np.array(nonzero[1])
            bbox = ((np.min(nonzerox), np.min(nonzeroy)), (np.max(nonzerox), np.max(nonzeroy)))
            # Draw the box on the image
            cv2.rectangle(img, bbox[0], bbox[1], boxcolor, 2)
        # Return the image
        return img

    def find_signs(self,img):
        startx = 30
        stopx = 50 #imgsize[0]-windowsize[0] #80
        starty = 10 #20 #19
        stopy = 36 #imgsize[1]-windowsize[1] #30

        window_list = []
        for x in range(startx, stopx, slidestep[0]):
            for y in range(starty, stopy, slidestep[1]):
                img_in = img[ y:y+windowsize[1], x:x+windowsize[0]]
                #img_crop_pp = imagefunctions.preprocess_one_rgb(img_crop)
                #img_in = np.array(255*img_crop_pp, dtype=np.uint8)
                if (imagefunctions.num_red_pixels(img_in)>min_red_pixels):
                    window_list.append(((x, y), (x+windowsize[0], y+windowsize[1])))

        #stop_windows, warn_windows = self.search_windows(img, window_list, framenum=random.randint(0,9999))
        stop_windows, warn_windows = self.search_windows(img, window_list)

        if ((len(stop_windows)<2) and (len(warn_windows)<2)):
            return 0,[None]
        elif (len(stop_windows)>=len(warn_windows)):
            return 1,[None]
        else:
            return 2,[None]
        # heatmap
        heat_stop = np.zeros_like(img[:,:,0]).astype(np.float)
        heat_warn = np.zeros_like(img[:,:,0]).astype(np.float)
        for bbox in window_list:
            startx = bbox[0][0]
            starty = bbox[0][1]
            endx = bbox[1][0]
            endy = bbox[1][1]
            cv2.rectangle(img,(startx, starty),(endx, endy),(0,0,200),1)
        for bbox in warn_windows:
            startx = bbox[0][0]
            starty = bbox[0][1]
            endx = bbox[1][0]
            endy = bbox[1][1]
            heat_warn[starty:endy, startx:endx] += 1.
            cv2.rectangle(img,(startx, starty),(endx, endy),(0,255,0),1)
        for bbox in stop_windows:
            startx = bbox[0][0]
            starty = bbox[0][1]
            endx = bbox[1][0]
            endy = bbox[1][1]
            heat_stop[starty:endy, startx:endx] += 1.
            cv2.rectangle(img,(startx, starty),(endx, endy),(255,0,0),1)

        score_stop = np.max(heat_stop)
        score_warn = np.max(heat_warn)
        #print '[scores] stop:' + str(score_stop) + ' warn:' + str(score_warn)

        detthresh = 4
        mapthresh = 10
        labels=[None]
        if score_stop<detthresh and score_warn<detthresh:
            #print 'NO SIGN'
            decision = 0
            draw_img = img
        elif score_stop>score_warn:
            #print 'STOP'
            decision = 1
            heatmap_stop = heat_stop
            heatmap_stop[heatmap_stop <= mapthresh] = 0
            labels = label(heatmap_stop)
            #draw_img = draw_labeled_bboxes(np.copy(img), labels_stop, boxcolor=(255,0,0))
        else:
            #print 'WARNING'
            decision = 2
            # draw box
            heatmap_warn = heat_warn
            heatmap_warn[heatmap_warn <= mapthresh] = 0
            labels = label(heatmap_warn)
            #draw_img = draw_labeled_bboxes(np.copy(img), labels_warn, boxcolor=(0,255,0))

        #Image.fromarray(draw_img).show()
        return decision, labels #draw_img

    def processOneFrame(self,img):
        dec, labels = self.find_signs(img)
        self.tracker.new_data(dec)
        final_decision = self.tracker.combined_results()
        #print dec, final_decision
        draw_img = img
        if len(labels)==2:
            if final_decision==1:
                draw_img = self.draw_labeled_bboxes(np.copy(img), labels, boxcolor=(255,0,0))
            elif final_decision==2:
                draw_img = self.draw_labeled_bboxes(np.copy(img), labels, boxcolor=(0,255,0))
            else:
                draw_img = img
        return final_decision, draw_img

if __name__ == '__main__':
    SVMCLF()
