import pickle
import  matplotlib.pyplot as plt
import numpy as np
from sklearn.model_selection import train_test_split
import cv2
import random
import pandas as pd
import ImageFunctions as imagefunctions
from sklearn.utils import shuffle

# Load pickled data
data_all = pickle.load(open('data.p', 'rb'))
X_all, y_all = data_all['images'], data_all['labels']
X_train, X_valid, y_train, y_valid = train_test_split(X_all, y_all, test_size=0.20, random_state=42)

assert(len(X_train) == len(y_train))
assert(len(X_valid) == len(y_valid))
print 'Original training samples: ' + str(len(X_train))
# convert to numpy
X_train = np.array(X_train)
X_valid = np.array(X_valid)
y_train = np.array(y_train)
y_valid = np.array(y_valid)

# data augmentation
X_rot = []
y_rot = []
for X,y in zip(X_train,y_train):
    for r in range(1,4):
        imrot = np.rot90(X,r)
        X_rot.append(imrot)
        y_rot.append(y)
X_train = np.append(X_train, X_rot, axis=0)
y_train = np.append(y_train, y_rot)

# check data
# Number of training examples# Numbe
n_train = X_train.shape[0]
# Number of testing examples.
n_valid = X_valid.shape[0]
# Shape of traffic sign image
image_shape = X_train[0].shape
# How many unique classes/labels there are in the dataset.
classes = np.unique(y_train)
n_classes = len(classes)

print('Images loaded.')
print "Training samples: " + str(n_train)
print "Validation samples: " + str(n_valid)
print "Image data shape: " + str(image_shape)
print "Classes: " + str(classes) + "\n"
# ------------------------------------------------------------------ #

# Pre-Process
## Pre-Process: RGB
X_train_prep = imagefunctions.preprocess_rgb(X_train)
X_valid_prep = imagefunctions.preprocess_rgb(X_valid)
## Pre-Process: Grayscale
#X_train_prep = imagefunctions.preprocess_grayscale(X_train)
#X_valid_prep = imagefunctions.preprocess_grayscale(X_valid)

# check quality after pre-processing
check_quality = False
if (check_quality):
    index = random.randint(0, len(X_train))
    print("Random Test for {0}".format(y_train[index]))
    plt.figure(figsize=(5,5))

    plt.subplot(1, 2, 1)
    plt.imshow(X_train[index].squeeze())
    plt.title("Before")

    plt.subplot(1, 2, 2)
    if (proc_num_channels==1):
        plt.imshow(X_train_prep[index].squeeze(), cmap="gray")
    else:
        plt.imshow(X_train_prep[index].squeeze())
    plt.title("After")
    plt.show()

# replace data with preprocessed images
X_train = X_train_prep
X_valid = X_valid_prep

print('Pre-processing done.')
# ------------------------------------------------------------------ #
import tensorflow as tf

EPOCHS = 15
BATCH_SIZE = 70

from tensorflow.contrib.layers import flatten

NChannels = 3 #proc_num_channels

def LeNet(x):    
    # Hyperparameters
    mu = 0
    sigma = 0.1
    
    # Layer 1: Convolutional. Input = 50x50x1. Output = 46x46x6.
    conv1_W = tf.Variable(tf.truncated_normal(shape=(5, 5, NChannels, 6), mean = mu, stddev = sigma))
    conv1_b = tf.Variable(tf.zeros(6))
    conv1   = tf.nn.conv2d(x, conv1_W, strides=[1, 1, 1, 1], padding='VALID') + conv1_b

    # Activation - relu.
    conv1 = tf.nn.relu(conv1)

    # Pooling. Input = 46x46x6. Output = 23x23x6.
    conv1 = tf.nn.max_pool(conv1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

    ##############################################################
    # conv2 - Design one more convolutional layer
    #
    # Layer 2: Convolutional
    # Activation - relu
    # Pooling. 
    ##############################################################

    # Flatten. 
    fc0   = flatten(conv2)

    ##############################################################
    # fc1 - Design one fully connected layer with output dimension 120
    #     
    # Layer 3: Fully Connected. Input = ???. Output = 120.
    # Activation - relu.
    ##############################################################

    ##############################################################
    # Optional: dropout
    #fc1_drop = tf.nn.dropout(fc1, keep_prob)
    ##############################################################
    
    # Layer 4: Fully Connected. Input = 120. Output = 84.
    fc2_W  = tf.Variable(tf.truncated_normal(shape=(120, 84), mean = mu, stddev = sigma))
    fc2_b  = tf.Variable(tf.zeros(84))
    fc2    = tf.matmul(fc1, fc2_W) + fc2_b # no drop-out
    
    # Activation.
    fc2    = tf.nn.relu(fc2)
    
    # dropout
    fc2_drop = tf.nn.dropout(fc2, keep_prob)

    # Layer 5: Fully Connected. Input = 84. Output = n_classes.
    fc3_W  = tf.Variable(tf.truncated_normal(shape=(84, n_classes), mean = mu, stddev = sigma))
    fc3_b  = tf.Variable(tf.zeros(n_classes))
    logits = tf.matmul(fc2_drop, fc3_W) + fc3_b # with drop-out
    
    # For L2-regularization
    l2loss_hidden_weights = tf.nn.l2_loss(fc2_W)
    l2loss_out_weights = tf.nn.l2_loss(fc3_W)
    
    return logits, l2loss_hidden_weights, l2loss_out_weights
# ------------------------------------------------------------------ #

### Train model

x = tf.placeholder(tf.float32, (None, 50, 50, NChannels)) # 3-channel RGB images
y = tf.placeholder(tf.int32, (None))
one_hot_y = tf.one_hot(y, n_classes)

# dropout keep probability
keep_prob = tf.placeholder(tf.float32)

rate = 0.001
beta = 0.0001 # for L2 regularization - 0.0=turn off

#logits = LeNet(x)
logits, l2loss_hidden_weights, l2loss_out_weights = LeNet(x)
#cross_entropy = tf.nn.softmax_cross_entropy_with_logits(logits = logits, labels=one_hot_y)
cross_entropy = tf.nn.softmax_cross_entropy_with_logits_v2(logits = logits, labels=one_hot_y)

#loss_operation = tf.reduce_mean(cross_entropy)
loss_operation = tf.reduce_mean(cross_entropy + 
    beta*l2loss_hidden_weights +
    beta*l2loss_out_weights) # do not apply L2 regularization on biases

optimizer = tf.train.AdamOptimizer(learning_rate = rate)
training_operation = optimizer.minimize(loss_operation)

correct_prediction = tf.equal(tf.argmax(logits, 1), tf.argmax(one_hot_y, 1))
accuracy_operation = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
saver = tf.train.Saver()

def evaluate(X_data, y_data, kprob):
    num_examples = len(X_data)
    total_accuracy = 0
    sess = tf.get_default_session()
    for offset in range(0, num_examples, BATCH_SIZE):
        batch_x, batch_y = X_data[offset:offset+BATCH_SIZE], y_data[offset:offset+BATCH_SIZE]
        accuracy = sess.run(accuracy_operation, feed_dict={x: batch_x, y: batch_y, keep_prob: kprob})
        total_accuracy += (accuracy * len(batch_x))
    return total_accuracy / num_examples

with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    num_examples = len(X_train)
    
    print("Training...")
    print()
    for i in range(EPOCHS):
        # Shuffle X_train, y_train again for each EPOCH
        X_train, y_train = shuffle(X_train, y_train)
        for offset in range(0, num_examples, BATCH_SIZE):
            end = offset + BATCH_SIZE
            batch_x, batch_y = X_train[offset:end], y_train[offset:end]
            sess.run(training_operation, feed_dict={x: batch_x, y: batch_y, keep_prob: 0.4})

        validation_accuracy = evaluate(X_valid, y_valid, 1.0)
        print("EPOCH {} ...".format(i+1))
        print("Validation Accuracy = {:.3f}".format(validation_accuracy))
        print()
        
    saver.save(sess, './lenet')
    print("Model saved")

print('CNN training done.')

# ------------------------------------------------------------------ #

## test data

# Load pickled data
data_test = pickle.load(open('test.p', 'rb'))
X_test, y_test = data_test['images'], data_test['labels']

# convert to numpy
X_test = np.array(X_test)
y_test = np.array(y_test)

# pre-process
X_test = imagefunctions.preprocess_rgb(X_test)

with tf.Session() as sess:
    saver.restore(sess, tf.train.latest_checkpoint('.'))

    test_accuracy = evaluate(X_test, y_test, 1.0)
    print("Test Accuracy = {:.3f}".format(test_accuracy))



