from keras.optimizers import Adam
from keras.layers import Dropout, Flatten, Conv1D, Conv2D, MaxPool1D, MaxPool2D, BatchNormalization, Convolution2D,MaxPooling2D
from keras.layers import Input, Dense, Masking, Merge, Permute, Reshape
from keras.models import Sequential, Model
from keras import optimizers, losses, activations, models
import numpy as np # linear algebra
import tensorflow as tf
from capsulelayers import CapsuleLayer, PrimaryCap, Length, Mask
from tensorflow import keras

def margin_loss(y_true, y_pred):
	"""
	Margin loss for Eq.(4). When y_true[i, :] contains not just one `1`, this loss should work too. Not test it.
	:param y_true: [None, n_classes]
	:param y_pred: [None, num_capsule]
	:return: a scalar loss value.
	"""
	L = y_true * tf.square(tf.maximum(0., 0.9 - y_pred)) + \
	    0.5 * (1 - y_true) * tf.square(tf.maximum(0., y_pred - 0.1))
	
	return tf.reduce_mean(tf.reduce_sum(L, 1))

# def make_CapsNet(x_shape, n_class, trainable = True, num_routing=3):
# 	"""
# 	A Capsule Network on MNIST.
# 	:param input_shape: data shape, 2d, [width, height]
# 	:param n_class: number of classes
# 	:param num_routing: number of routing iterations
# 	:return: Two tensorflow.keras Models, the first one used for training, and the second one for evaluation.
# 	        `eval_model` can also be used for training.
# 	"""
# 	x = Input(shape=x_shape)
# 	
# 	# Layer 1: Just a conventional Conv2D layer
# 	conv1 = Conv2D(filters=256, kernel_size=9, strides=1, padding='valid', activation='relu', name='conv1')(x)
# 	
# 	# Layer 2: Conv2D layer with `squash` activation, then reshape to [None, num_capsule, dim_capsule]
# 	primarycaps = PrimaryCap(conv1, dim_capsule=8, n_channels=32, kernel_size=9, strides=2, padding='valid')
# 	
# 	# Layer 3: Capsule layer. Routing algorithm works here.
# 	digitcaps = CapsuleLayer(num_capsule=n_class, dim_capsule=16, num_routing=num_routing,
# 	                         name='digitcaps')(primarycaps)
# 	
# 	# Layer 4: This is an auxiliary layer to replace each capsule with its length. Just to match the true label's shape.
# 	# If using tensorflow, this will not be necessary. :)
# 	out_caps = Length(name='capsnet')(digitcaps)
# 	
# 	# Decoder network.
# 	y = Input(shape=(n_class,))
# 	masked_by_y = Mask()([digitcaps, y])  # The true label is used to mask the output of capsule layer. For training
# 	masked = Mask()(digitcaps)  # Mask using the capsule with maximal length. For prediction
# 	
# 	# Shared Decoder model in training and prediction
# 	decoder = Sequential(name='decoder')
# 	decoder.add(Dense(512, activation='relu', input_dim=16*n_class))
# 	decoder.add(Dense(1024, activation='relu'))
# 	decoder.add(Dense(np.prod(x_shape), activation='sigmoid'))
# 	decoder.add(Reshape(target_shape=x_shape, name='out_recon'))
# 	
# 	model = None
# 	# Models for training and evaluation (prediction)
# 	if trainable:
# 		model = Model([x, y], [out_caps, decoder(masked_by_y)])
# 	else:
# 		model = Model(x, [out_caps, decoder(masked)])
# 		
# 	model.compile(optimizer="adam",
# 				  loss=[margin_loss, 'mse'],
# 				  loss_weights=[1., 0.392],
# 				  metrics={'capsnet': 'accuracy'})
# 	
# 	return model


def make_lr_decay(lr=0.001):
	lr_decay = keras.callbacks.LearningRateScheduler(schedule=lambda epoch: lr * (0.9 ** epoch))
	return lr_decay

def make_CapsNet(input_shape, n_class, trainable = True, num_routing=3):
	"""
	A Capsule Network on MNIST.
	:param input_shape: data shape, 3d, [width, height, channels]
	:param n_class: number of classes
	:param num_routing: number of routing iterations
	:return: Two tensorflow.keras Models, the first one used for training, and the second one for evaluation.
	        `eval_model` can also be used for training.
	"""
	x = keras.layers.Input(shape=input_shape)
	
	# Layer 1: Just a conventional Conv2D layer
	conv1 = keras.layers.Conv2D(filters=64, kernel_size=9, strides=1, padding='valid', activation='relu', name='conv1')(x)
	
	# Layer 2: Conv2D layer with `squash` activation, then reshape to [None, num_capsule, dim_capsule]
	primarycaps = PrimaryCap(conv1, dim_capsule=5, n_channels=32, kernel_size=9, strides=2, padding='valid')
	
	# Layer 3: Capsule layer. Routing algorithm works here.
	digitcaps = CapsuleLayer(num_capsule=n_class, dim_capsule=16, num_routing=num_routing,
	                         name='digitcaps')(primarycaps)
	
	# Layer 4: This is an auxiliary layer to replace each capsule with its length. Just to match the true label's shape.
	# If using tensorflow, this will not be necessary. :)
	out_caps = Length(name='capsnet')(digitcaps)
	
	# Decoder network.
	y = keras.layers.Input(shape=(n_class,))
	masked_by_y = Mask()([digitcaps, y])  # The true label is used to mask the output of capsule layer. For training
	masked = Mask()(digitcaps)  # Mask using the capsule with maximal length. For prediction
	
	# Shared Decoder model in training and prediction
	decoder = keras.models.Sequential(name='decoder')
	decoder.add(keras.layers.Dense(128, activation='relu', input_dim=16*n_class))
	decoder.add(keras.layers.Dense(512, activation='relu'))
	decoder.add(keras.layers.Dense(np.prod(input_shape), activation='sigmoid'))
	decoder.add(keras.layers.Reshape(target_shape=input_shape, name='out_recon'))
	
	# Models for training and evaluation (prediction)
	if trainable:
		model = keras.models.Model([x, y], [out_caps, decoder(masked_by_y)])
	else:
		model = keras.models.Model(x, [out_caps, decoder(masked)])
		
	keras.backend.get_session().run(tf.global_variables_initializer())
	
	model.compile(optimizer=keras.optimizers.Adam(lr=0.01),
				  loss=[margin_loss, 'mse'],
				  loss_weights=[1., 0.392],
				  metrics=["accuracy"])
	
	
	return model

def make_cnn1(x_shape, cls_num, trainable = True):
	
	model = Sequential()
	
	model.add(Conv2D(filters = 8, kernel_size = (2, 2), activation='relu',
	                 input_shape = (x_shape[0], x_shape[1], 1)))
	
	model.add(Conv2D(filters = 8, kernel_size = (2, 2), activation='relu'))
	model.add(MaxPool2D(strides=(2, 2)))
	model.add(Dropout(0.2))
	model.add(Conv2D(filters = 16, kernel_size = (3, 3), activation='relu'))
	model.add(Conv2D(filters = 16, kernel_size = (3, 3), activation='relu'))
	model.add(MaxPool2D(strides=(2, 2)))
	model.add(Dropout(0.2))
	model.add(Conv2D(filters = 32, kernel_size = (3, 3), activation='relu'))
	model.add(MaxPool2D(strides=(2,2)))
	model.add(Dropout(0.2))
	
# 	model.add(Conv2D(filters = 32, kernel_size = (3, 3), activation='relu'))
# 	model.add(BatchNormalization())
	#     model.add(Conv2D(filters = 32, kernel_size = (3, 3), activation='relu'))
	#     model.add(BatchNormalization())
	#     model.add(Conv2D(filters = 32, kernel_size = (3, 3), activation='relu'))
	#     model.add(BatchNormalization())
	#     model.add(MaxPool2D(strides=(2,2)))
	
	model.add(Flatten())
	
	model.add(Dense(128, activation='relu'))
	model.add(BatchNormalization())
	model.add(Dense(128, activation='relu'))
	model.add(BatchNormalization())
	model.add(Dense(cls_num, activation='softmax'))
	model.trainable = trainable
	model.compile(loss="binary_crossentropy", optimizer="adam", metrics=["accuracy"])
	return model
