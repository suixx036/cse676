# -*- coding: utf-8 -*-
"""DenseNet.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/185xMwZAAnJ9sodKkOKaWa3WxJ4HxyFVo
"""

import keras
import math
import numpy as np
from keras.layers.normalization import BatchNormalization
from keras.layers import Conv2D, Dense, Input, add, Activation, AveragePooling2D, GlobalAveragePooling2D, Lambda, concatenate
from keras.initializers import he_normal
from keras.layers.merge import Concatenate
from keras.callbacks import LearningRateScheduler, TensorBoard, ModelCheckpoint
from keras.models import Model
from keras.datasets import cifar10
from keras.preprocessing.image import ImageDataGenerator
from keras import optimizers, regularizers

growth_rate        = 12 
depth              = 100
compression        = 0.5

img_rows, img_cols = 32, 32
img_channels       = 3
num_classes        = 10
batch_size         = 64         # 64 or 32 or other
epochs             = 300
iterations         = 782       
weight_decay       = 1e-4

mean = [125.307, 122.95, 113.865]
std  = [62.9932, 62.0887, 66.7048]

from keras import backend as K
if('tensorflow' == K.backend()):
    import tensorflow as tf
    from keras.backend.tensorflow_backend import set_session
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    sess = tf.Session(config=config)

def sc(epoch):
    if epoch < 140:
        return 0.1
    if epoch < 245:
        return 0.01
    return 0.001

def d_net(img_input,classes_num):
    def conv_l(x, out_filters, k_size):
        return Conv2D(filters=out_filters,kernel_size=k_size,strides=(1,1),padding='same',kernel_initializer='he_normal',kernel_regularizer=regularizers.l2(weight_decay),use_bias=False)(x)

    def d_layer(x):
        return Dense(units=classes_num,
                     activation='softmax',
                     kernel_initializer='he_normal',
                     kernel_regularizer=regularizers.l2(weight_decay))(x)

    def bn_relu(x):
        x = BatchNormalization(momentum=0.9, epsilon=1e-5)(x)
        x = Activation('relu')(x)
        return x

    def b_len_eck(x):
        channels = growth_rate * 4
        x = bn_relu(x)
        x = conv_l(x, channels, (1,1))
        x = bn_relu(x)
        x = conv_l(x, growth_rate, (3,3))
        return x

    def single(x):
        x = bn_relu(x)
        x = conv_l(x, growth_rate, (3,3))
        return x

    def trans(x, inchannels):
        outchannels = int(inchannels * compression)
        x = bn_relu(x)
        x = conv_l(x, outchannels, (1,1))
        x = AveragePooling2D((2,2), strides=(2, 2))(x)
        return x, outchannels

    def d_block(x,blocks,nchannels):
        concat = x
        for i in range(blocks):
            x = b_len_eck(concat)
            concat = concatenate([x,concat], axis=-1)
            nchannels += growth_rate
        return concat, nchannels


    nblocks = (depth - 4) // 6 
    nchannels = growth_rate * 2


    x = conv_l(img_input, nchannels, (3,3))
    x, nchannels = d_block(x,nblocks,nchannels)
    x, nchannels = trans(x,nchannels)
    x, nchannels = d_block(x,nblocks,nchannels)
    x, nchannels = trans(x,nchannels)
    x, nchannels = d_block(x,nblocks,nchannels)
    x = bn_relu(x)
    x = GlobalAveragePooling2D()(x)
    x = d_layer(x)
    return x


if __name__ == '__main__':

    (x_train, y_train), (x_test, y_test) = cifar10.load_data()
    y_train = keras.utils.to_categorical(y_train, num_classes)
    y_test  = keras.utils.to_categorical(y_test, num_classes)
    x_train = x_train.astype('float32')
    x_test  = x_test.astype('float32')

    for i in range(3):
        x_train[:,:,:,i] = (x_train[:,:,:,i] - mean[i]) / std[i]
        x_test[:,:,:,i] = (x_test[:,:,:,i] - mean[i]) / std[i]


    img_input = Input(shape=(img_rows,img_cols,img_channels))
    output    = d_net(img_input,num_classes)
    model     = Model(img_input, output)
    
    print(model.summary())

    sgd = optimizers.SGD(lr=.1, momentum=0.9, nesterov=True)
    model.compile(loss='categorical_crossentropy', optimizer=sgd, metrics=['accuracy'])

    tb_cb     = TensorBoard(log_dir='./densenet/', histogram_freq=0)
    change_lr = LearningRateScheduler(sc)
    pt_ck      = ModelCheckpoint('./ckpt.h5', save_best_only=False, mode='auto', period=10)
    ks_cb      = [change_lr,tb_cb,pt_ck]

    print('Using real-time data augmentation.')
    datagen   = ImageDataGenerator(horizontal_flip=True,width_shift_range=0.125,height_shift_range=0.125,fill_mode='constant',cval=0.)

    datagen.fit(x_train)

    model.fit_generator(datagen.flow(x_train, y_train,batch_size=batch_size), steps_per_epoch=iterations, epochs=epochs, callbacks=ks_cb,validation_data=(x_test, y_test))
    model.save('densenet.h5')