#!/usr/bin/env python

from numpy import *
from matplotlib.pylab import *
from mpl_toolkits.mplot3d import Axes3D
import tensorflow as tf



import cv2
import cPickle as pickle

import numpy as np
import matplotlib.pyplot as plt
import keras

import time
import random
import scipy
import math
import matplotlib.animation as animation

from keras.models import Model
from keras.layers import Activation, Dense, Input, Multiply
from keras.layers import Conv2D, Flatten, Reshape, Conv2DTranspose
from keras.layers import Dot, Lambda, Concatenate, RepeatVector
from keras.utils import plot_model
from PIL import Image
from keras.constraints import max_norm, non_neg

matplotlib.rcParams.update({'font.size': 16})
L1=0.3
L2=0.3
img_size = 64
input_encoder_shape = (img_size, img_size,2)
latent_dim = 32
input_decoder_shape = (1, 2*latent_dim,)

def randrange(n, vmin, vmax):
    return (vmax-vmin)*rand(n) + vmin

def generate_posture(state=randrange(4, 0, 2*pi),L1=0.3,L2=0.3):
    """ function generating  a random posture from random joint state

    Args :
        state : state
        L1 : length of arm1
        L2 : length of arm2
    Returns :
        x,y,z : position of end effector
    """
    state[3] = 0 # NEW 170111
    x = cumsum([0,L1 * cos(state[0]) * cos(state[2]), L2 * cos(state[0]+state[1]) * cos(state[2]+state[3])])
    y = cumsum([0,L1 * cos(state[0]) * sin(state[2]), L2 * cos(state[0]+state[1]) * sin(state[2]+state[3])])
    z = cumsum([0,L1 * sin(state[0]), L2 * sin(state[0]+state[1])])
    return x,y,z

def generate_random_robot_data(n,L1=0.3,L2=0.3 ):
    """ function generating n random states

    Args :
        n : number of states to generate
        L1 : same as before
        L1 : same as before

    Returns :
        a tuple of np arrays
        phi1, phi2, theta1 : joint angles
        x,y,z : end effector position
        vx,vy,vz: speed i guess...
    """
    phi1 = randrange(n, 0, 2*pi)
    theta1 = randrange(n, 0, 2*pi)
    phi2 = randrange(n, 0, 2*pi)
    theta2 =  zeros(n)
    x = L1 * cos(phi1) * cos(theta1) + L2 * cos(phi1 + phi2) * cos(theta1 + theta2) # ELBOW + HAND
    y = L1 * cos(phi1) * sin(theta1) + L2 * cos(phi1 + phi2) * sin(theta1 + theta2) # ELBOW + HAND
    z = L1 * sin(phi1)               + L2 * sin(phi1 + phi2) # ELBOW + HAND
    vx=L2 * cos(phi1 + phi2) * cos(theta1 + theta2)
    vy=L2 * cos(phi1 + phi2) * sin(theta1 + theta2)
    vz=L2 * sin(phi1 + phi2)
    return (phi1,phi2,theta1,x,y,z,vx,vy,vz)


def control_robot(phi1,phi2,theta1, theta2):
    """function calculating end effector postion from joint angles

    Args :
        phi1, phi2, theta1, theta2 : joint angles (4 dof arm )

    Returns:
        x,y,z : end effector position
        vx,vy,vz : speed i guess...
    """
    x = L1 * cos(phi1) * cos(theta1) + L2 * cos(phi1 + phi2) * cos(theta1 + theta2) # ELBOW + HAND
    y = L1 * cos(phi1) * sin(theta1) + L2 * cos(phi1 + phi2) * sin(theta1 + theta2) # ELBOW + HAND
    z = L1 * sin(phi1)               + L2 * sin(phi1 + phi2) # ELBOW + HAND
    vx=L2 * cos(phi1 + phi2) * cos(theta1 + theta2)
    vy=L2 * cos(phi1 + phi2) * sin(theta1 + theta2)
    vz=L2 * sin(phi1 + phi2)
    return (x,y,z,vx,vy,vz)

def plot_arm(phi1, phi2, theta1, time):
    """function ploting and saving in /images 3d arm plot
    from arg joint state

    Args :
        phi1, phi2, theta1 : joint angles (3 dof arm )

    Returns :
        ax : a matplotlib figure object
    """
    fig = figure(facecolor=(0.0,0.0,0.0))
    ax = fig.gca(projection='3d')
    x = [0, 0, L1 * cos(phi1) * cos(theta1), L2 * cos(phi1 + phi2) * cos(theta1)]
    y = [0, 0, L1 * cos(phi1) * sin(theta1), L2 * cos(phi1 + phi2) * sin(theta1)] # ELBOW + HAND
    z = [0, 0, L1 * sin(phi1) , L2 * sin(phi1 + phi2)] # ELBOW + HAND
    # ax.plot(x[0:1], y[0:1], z[0:1], label='shoulder', lw=2, color= 'k')
    # ax.plot(x[2:3], y[2:3], z[2:3], label='elbow', lw=2, color= 'c')
    # Hide grid lines
    ax.grid(False)
    # ax.set_autoscale_on(True)
    ax.set_facecolor((0.0,0.0,0.0))

    ax.set_xlim(left=-0.2, right=0.2)
    ax.set_ylim(bottom=-0.2, top=0.2)
    ax.set_zlim(bottom=-0.2, top=0.2)
    ax.axis('off')
    # Hide axes ticks
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    ax.plot(x, y, z, label='shoulder', lw=5, color= 'white')
    filename = 'images/%s.png' %time
    savefig(filename, facecolor=fig.get_facecolor(), edgecolor='none')
    close()

    return ax

def create_random_data(nb_posture, nb_command, typ = 'train'):
    """ func creates nb_posture random joint angles and nb_command random command
    and plots and saves the corresponding fig and returns corresponding commands

    Args :
        nb_posture : nb of posture to be created
        nb_command : nb of command to be generated

    Returns :
        train_data_h : corresponding commands
    """

    posture = zeros((nb_posture, 4))
    posture[:,0] = randrange(nb_posture, 0, 2*pi)
    posture[:,1] = randrange(nb_posture, 0, 2*pi)
    posture[:,2] = randrange(nb_posture, 0, 2*pi)

    command = zeros((nb_command, 4))
    command[:,0] = randrange(nb_command, 0, 1)*0.5
    command[:,1] = randrange(nb_command, 0, 1)*0.5
    command[:,2] = randrange(nb_command, 0, 1)*0.5

    nb_data = nb_posture*nb_command

    train_data_x = zeros((nb_data, 1, 4))
    train_data_y = zeros((nb_data, 1, 4))
    train_data_h = zeros((nb_data, 1, 4))

    idx = 0
    for i in range(nb_posture):
        for j in range(nb_command):
            train_data_x[idx] = posture[i]
            idx = idx + 1

    idx = 0
    for i in range(nb_posture):
        for j in range(nb_command):
            train_data_y[idx] = posture[i]  + command[j]
            idx = idx + 1

    idx = 0
    for i in range(nb_posture):
        for j in range(nb_command):
            train_data_h[idx] = command[j]
            idx = idx + 1

    for i in range(nb_data):
        pos0, pos1, pos2, pos3 = train_data_x[i][0]
        dpos0, dpos1, dpos2, dpos3 = train_data_y[i][0]

        before = typ + '/fig_before_%s' %i
        after = typ + '/fig_after_%s' %i
        plot_arm(pos0, pos1, pos2, before)
        plot_arm(dpos0, dpos1, dpos2, after)

    return train_data_x, train_data_y, train_data_h

def gaussian_kernel(size, mean, std):
    """Makes 2D gaussian Kernel for convolution."""

    d = tf.distributions.Normal(mean, std)
    vals = d.prob(tf.range(start = -size, limit = size + 1, dtype = tf.float32))
    gauss_kernel = tf.einsum('i,j->ij', vals, vals)

    return gauss_kernel / tf.reduce_sum(gauss_kernel)

def load_and_process_images(nb_data, typ):
    """
    Args :
        nb_data : number of images pairs to process
        typ : train or test
    Returns :
        a tensor of shape (nb_data, image_shape)
    """
    tmp = []

    for i in range(nb_data):
        before = 'images/' + typ  + '/fig_before_%s.png' %i
        after = 'images/' + typ + '/fig_after_%s.png' %i

        tens_before = load_and_preprocess_image(before)
        tens_after = load_and_preprocess_image(after)

        t = tf.concat([tens_before, tens_after], -1)

        tf.reshape(t, [img_size,img_size,2])
        tmp.append(t)

    return tf.stack(tmp)

def preprocess_image(img):
    """decode, resize and normalize a image
    """
    tmp = tf.image.decode_png(img, channels=1)
    tmp = tf.image.resize(tmp, [img_size, img_size])
    #gauss_kernel = gaussian_kernel(3, 0.0, 1.0)
    #gauss_kernel = gauss_kernel[:,:, tf.newaxis, tf.newaxis]
    #tmp = tf.nn.conv2d(tmp, gauss_kernel, strides=[1, 1, 1, 1], padding="SAME")
    tmp /= 255.0  # normalize to [0,1] range
    return tmp

def load_and_preprocess_image(path):
    image = tf.io.read_file(path)

    return preprocess_image(image)

@tf.function
def compute_conv_loss(model, img, filter_index ):
    """compute loss for filter visualization

    Args :
        model : a tf.keras.Model object (preferably a convnet use compute_loss for others)
        img : an input image of shape model.input
        filter_index : a filter index for convnet

    Returns :
        loss : mean of filter_index filter output
    """
    output = model(img)
    loss = tf.keras.backend.mean(output[:,:,:,filter_index]) #depends on the filter to analyze
    return loss

def generate_conv_pattern(model, filter_index, nb_pass):
    """ generate an input image which maximizes the computed filter loss
        for conv layers, uses generate_pattern for others

    Args :
        filter_index : the filter to compute
        nb_pass : number of calcul_loss iteration

    Returns :
        tmp : updated input image
    """
    input_img_data = tf.convert_to_tensor(np.random.random(( 1, 64,64, 1)), dtype='float32') * 2 + 1.
    tmp = tf.compat.v1.get_variable('tmp', dtype=tf.float32, initializer=input_img_data)

    with tf.GradientTape(persistent=True) as tape:
        tape.watch(tmp)
        loss = compute_conv_loss(model, tmp, filter_index)

    for i in range(nb_pass):
        grads = tape.gradient(loss, tmp, unconnected_gradients='zero')
        tmp.assign_add(grads)

    return tmp[0][:,:,:]
@tf.function
def compute_loss(model, img, filter_index):
    """compute loss for filter visualization

    Args :
        model : a tf.keras.Model object
        img : an input image of shape model.input
        filter_index : a filter index for convnet

    Returns :
        loss : mean of filter_index filter output
    """
    output = model(img)
    loss = (output[0][:,filter_index])
    return loss

def generate_pattern(model, filter_index, nb_pass):
    """ generate an input image which maximizes the computed filter loss

    Args :
        filter_index : the filter to compute
        nb_pass : number of calcul_loss iteration

    Returns :
        tmp : updated input image
    """

    input_img_data = tf.convert_to_tensor(np.random.random(( 1, 64,64, 2)), dtype='float32') * 2 + 1.
    tmp = tf.compat.v1.get_variable('tmp', dtype=tf.float32, initializer=input_img_data)

    with tf.GradientTape(persistent=True) as tape:
        tape.watch(tmp)
        loss = compute_loss(model, tmp, filter_index)

    for i in range(nb_pass):
        grads = tape.gradient(loss, tmp, unconnected_gradients='zero')
        tmp.assign_add(grads)

    return tmp[0][:,:,:1]

def build_dense_encoder():

    inputs = tf.keras.Input(shape = input_encoder_shape, name = 'encoder_input')

    x = tf.keras.layers.Lambda(lambda x: x[:,:,:,0])(inputs)
    x = tf.keras.layers.Reshape((img_size, img_size,1))(x)

    y = tf.keras.layers.Lambda(lambda x: x[:,:,:,1])(inputs)
    y = tf.keras.layers.Reshape((img_size, img_size,1))(y)

    fx = tf.keras.layers.Flatten()(x)
    fx = tf.keras.layers.Dense(latent_dim, activation = 'relu', name = 'latent_enc_fx1')(fx)
    #fx = tf.keras.layers.Dense(latent_dim, activation = 'relu', name = 'latent_enc_fx2')(fx)
    #fx = tf.keras.layers.Dense(latent_dim, activation = 'relu', name = 'latent_enc_fx3')(fx)
    fx = tf.keras.layers.Reshape((latent_dim,1,))(fx)

    fy = tf.keras.layers.Flatten()(y)
    fy = tf.keras.layers.Dense(latent_dim, activation = 'relu', name = 'latent_enc_fy1')(fy)
    #fy = tf.keras.Dense(latent_dim, activation = 'relu', name = 'latent_enc_fy2')(fy)
    #fy = tf.keras.Dense(latent_dim, activation = 'relu', name = 'latent_enc_fy3')(fy)
    fy = tf.keras.layers.Reshape((1,latent_dim,))(fy)

    matmul = tf.keras.layers.Multiply()([fx, fy])

    fh = tf.keras.layers.Flatten()(matmul)
    fh = tf.keras.layers.Dense(latent_dim, name = 'latent_fh1')(fh)
    #fh = tf.keras.layers.Dense(latent_dim, name = 'latent_fh2')(fh)
    #fh = tf.keras.layers.Dense(latent_dim, name = 'latent_fh3')(fh)

    fx = tf.keras.layers.Reshape((1, latent_dim,))(fx)
    fh = tf.keras.layers.Reshape((1,latent_dim,))(fh)

    outputs = tf.keras.layers.Concatenate()([fx, fh])
    encoder = tf.keras.Model(inputs = inputs, outputs = outputs, name = 'encoder_model')

    return encoder

def build_dense_decoder():

    inputs = tf.keras.Input(shape = input_decoder_shape, name = 'decoder_input')

    fx = tf.keras.layers.Lambda(lambda x: x[:,:,:latent_dim])(inputs)
    fx = tf.keras.layers.Reshape((latent_dim,1,))(fx)

    fh = tf.keras.layers.Lambda(lambda x: x[:,:,latent_dim:])(inputs)
    fh = tf.keras.layers.Reshape((latent_dim,1,))(fh)

    fh = tf.keras.layers.Flatten()(fh)
    fh = tf.keras.layers.Dense(latent_dim, name = 'latent_dec_fh1')(fh)
    fh = tf.keras.layers.Dense(latent_dim, name = 'latent_dec_fh2')(fh)
    fh = tf.keras.layers.Dense(latent_dim, name = 'latent_dec_fh3')(fh)
    fh = tf.keras.layers.Reshape((1,latent_dim,))(fh)

    matmul = tf.keras.layers.Multiply()([fx, fh])

    fy = tf.keras.layers.Flatten()(matmul)
    fy = tf.keras.layers.Dense(latent_dim, name = 'latent_dec_fy1')(fy)
    #fy = tf.keras.layers.Dense(latent_dim, name = 'latent_dec_fy2')(fy)
    #fy = tf.keras.layers.Dense(latent_dim, name = 'latent_dec_fy3')(fy)

    y = tf.keras.layers.Dense(img_size*img_size, activation = 'relu', name = 'y_recon')(fy)
    outputs = tf.keras.layers.Reshape((img_size, img_size,1))(y)

    decoder = tf.keras.Model(inputs = inputs, outputs = outputs, name = 'decoder_model')

    return decoder


def build_conv2D_encoder():

    inputs = tf.keras.Input(shape = input_encoder_shape, name = 'encoder_input')

    x = tf.keras.layers.Lambda(lambda x: x[:,:,:,0])(inputs)
    x = tf.keras.layers.Reshape((img_size, img_size,1))(x)

    y = tf.keras.layers.Lambda(lambda x: x[:,:,:,1])(inputs)
    y = tf.keras.layers.Reshape((img_size, img_size,1))(y)

    #fx = tf.keras.layers.Flatten()(x)
    fx = tf.keras.layers.Conv2D(filters=latent_dim, kernel_size=3, strides=(2,2),activation='relu', name='conv_x_1')(x)
    fx = tf.keras.layers.Conv2D(filters=latent_dim*2, kernel_size=3, strides=(2,2),activation='relu', name='conv_x_2')(fx)
    fx = tf.keras.layers.Flatten()(fx)
    #fx = tf.keras.layers.Dense(units=15*15*64, name = 'latent_fx1')(fx)
    fx = tf.keras.layers.Dense(latent_dim, name = 'latent_fx2')(fx)
    fx = tf.keras.layers.Reshape((latent_dim,1,))(fx)

    #fy = tf.keras.layers.Flatten()(y)
    fy = tf.keras.layers.Conv2D(filters=latent_dim, kernel_size=3, strides=(2,2),activation='relu', name='conv_y_1')(y)
    fy = tf.keras.layers.Conv2D(filters=latent_dim*2, kernel_size=3, strides=(2,2),activation='relu', name='conv_y_2')(fy)
    fy = tf.keras.layers.Flatten()(fy)
    #fy = tf.keras.layers.Dense(units=15*15*64, name = 'latent_fy1')(fy)
    fy = tf.keras.layers.Dense(latent_dim, name = 'latent_fy2')(fy)
    fy = tf.keras.layers.Reshape((1,latent_dim,))(fy)

    matmul = tf.keras.layers.Multiply()([fx, fy])

    fh = tf.keras.layers.Flatten()(matmul)
    fh = tf.keras.layers.Dense(latent_dim, name = 'latent_fh1')(fh)
    #fh = tf.keras.layers.Dense(latent_dim, name = 'latent_fh2')(fh)
    #fh = tf.keras.layers.Dense(latent_dim, name = 'latent_fh3')(fh)

    fx = tf.keras.layers.Reshape((1, latent_dim,))(fx)
    fh = tf.keras.layers.Reshape((1,latent_dim,))(fh)

    outputs = tf.keras.layers.Concatenate()([fx, fh])
    encoder = tf.keras.Model(inputs = inputs, outputs = outputs, name = 'encoder_model')

    return encoder

def build_conv2D_decoder():

    inputs = tf.keras.Input(shape = input_decoder_shape, name = 'decoder_input')

    fx = tf.keras.layers.Lambda(lambda x: x[:,:,:latent_dim])(inputs)
    fx = tf.keras.layers.Reshape((latent_dim,1,))(fx)

    fh = tf.keras.layers.Lambda(lambda x: x[:,:,latent_dim:])(inputs)

    fh = tf.keras.layers.Flatten()(fh)
    fh = tf.keras.layers.Dense(latent_dim, name = 'latent_dec_fh1')(fh)
    fh = tf.keras.layers.Dense(latent_dim, name = 'latent_dec_fh2')(fh)
    #fh = tf.keras.layers.Dense(latent_dim, name = 'latent_dec_fh3')(fh)
    fh = tf.keras.layers.Reshape((1,latent_dim,))(fh)

    matmul = tf.keras.layers.Multiply()([fx, fh])

    fy = tf.keras.layers.Flatten()(matmul)
    fy = tf.keras.layers.Dense(latent_dim/4*latent_dim/4*latent_dim*2, name = 'latent_dec_fy1')(fy)
    fy = tf.keras.layers.Reshape((latent_dim/4, latent_dim/4, 2*latent_dim))(fy)
    fy = tf.keras.layers.Conv2DTranspose(filters=latent_dim, activation='relu',kernel_size=3, strides=(2,2))(fy)
    fy = tf.keras.layers.Conv2DTranspose(filters=latent_dim/2, name = 'conv_trans_y_2', activation='relu', kernel_size=3, strides=(2,2))(fy)
    fy = tf.keras.layers.Conv2DTranspose(filters=latent_dim/4, name = 'conv_trans_y_3', activation='relu', kernel_size=3, strides=(2,2))(fy)
    fy = tf.keras.layers.Conv2DTranspose(1, name = 'conv_trans_y_4', activation='sigmoid', kernel_size=3, strides=(1,1))(fy)
    fy = tf.keras.layers.Cropping2D(cropping=((5,4), (4,5)))(fy)
    #y = tf.keras.layers.Dense(img_size*img_size, activation = 'relu', name = 'y_recon')(fy)
    outputs = tf.keras.layers.Reshape((img_size, img_size, 1))(fy)

    decoder = tf.keras.Model(inputs = inputs, outputs = outputs, name = 'decoder_model')

    return decoder
