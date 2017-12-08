import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt
from sklearn import preprocessing
from sklearn.cross_validation import train_test_split
from sklearn import metrics
from collections import Counter
from keras.utils.np_utils import to_categorical
import seaborn as sns
from sklearn import preprocessing
import os
import re
from glob import glob
import librosa
import random


sys.path.append('../../')
from base import data_util
from config import Config as cfg
from scipy.fftpack import fft
from scipy.io import wavfile
from scipy import signal
from python_speech_features import mfcc
from python_speech_features import logfbank




def standardization(X):
	x_t = preprocessing.scale(X, axis=0, with_mean=True, with_std=True, copy=True)
	return x_t
def call_feature_func(data, feats_name, is_normalized=False):
	feats = pd.DataFrame()
	for name in feats_name:
		func_name = "extract_{feat}_feature".format(feat = name)
		feats[name] = eval(func_name)(data, is_normalized)
	return feats





def extract_id_feature(data, is_normalized=False):
	def q_val(val):
		return val
	vals = data.apply(lambda x: q_val(x['id']), axis=1, raw=True)
	if is_normalized:
		vals = standardization(vals)
	return vals




def extract_all_features(df_list, is_normalized=False):
	data_all = pd.concat(df_list)
	feats_name = [
				'id',
				]

	feats = call_feature_func(data_all, feats_name, is_normalized)
	return feats








def extract_y_info(data):
	print 'Need to be implemented'
	return None





def gen_data(df_train, df_test, is_resample=False, is_normalized=False):
	x_train = extract_all_features([df_train], is_normalized)
	y_train = extract_y_info(df_train)



	x_test = extract_all_features([df_test], is_normalized)
	y_test = extract_y_info(df_test)



	x_t = x_train
	y_t = y_train
	if is_resample:
		x_t, y_t = data_util.resample(x_train, y_train)
	return x_t, y_t, x_test, y_test

def custom_fft(y, fs):
	T = 1.0 / fs
	N = y.shape[0]
	yf = fft(y)
	xf = np.linspace(0.0, 1.0/(2.0*T), N//2)
	# FFT is simmetrical, so we take just the first half
	# FFT is also complex, to we take just the real part (abs)
	vals = 2.0/N * np.abs(yf[0:N//2])
	return xf, vals

def logspecgram(audio, sample_rate, window_size=20,
                 step_size=10, eps=1e-10):
	nperseg = int(round(window_size * sample_rate / 1e3))
	noverlap = int(round(step_size * sample_rate / 1e3))
	freqs, times, spec = signal.spectrogram(audio,
	                                fs=sample_rate,
	                                window='hann',
	                                nperseg=nperseg,
	                                noverlap=noverlap,
	                                detrend=False)
	return np.log(spec.T.astype(np.float32) + eps)

def load_data(data_dir="../data/"):
	""" Return 2 lists of tuples:
	[(class_id, user_id, path), ...] for train
	[(class_id, user_id, path), ...] for validation
	"""
	# Just a simple regexp for paths with three groups:
	# prefix, label, user_id
	pattern = re.compile("(.+\/)?(\w+)\/([^_]+)_.+wav")
	all_files = glob(os.path.join(data_dir, 'train/audio/*/*wav'))
	
	with open(os.path.join(data_dir, 'train/validation_list.txt'), 'r') as fin:
		validation_files = fin.readlines()
	valset = set()
	for entry in validation_files:
		r = re.match(pattern, entry)
		if r:
			valset.add(r.group(3))

	possible = set(cfg.POSSIBLE_LABELS)
	train, val = [], []
	for entry in all_files:
		r = re.match(pattern, entry)
		if r:
			label, uid = r.group(2), r.group(3)
			if label == '_background_noise_':
				label = 'silence'
			if label not in possible:
				label = 'unknown'
			
			label_id = cfg.n2i(label)
			
			sample = (label_id, entry)
			if uid in valset:
				val.append(sample)
			else:
				train.append(sample)
	
	print('There are {} train and {} val samples'.format(len(train), len(val)))
	return train, val

def pad_audio(samples, max_len=cfg.sampling_rate):
	if len(samples) >= max_len: return samples
	else: return np.pad(samples, pad_width=(max_len - len(samples), 0), mode='constant', constant_values=(0, 0))

def get_wav(data, resampline_sil_rate=20, is_normalization=True):
	x = []
	y = []
	for (label_id, fname) in data:
# 		print fname
		_, wav = wavfile.read(fname)
		wav = pad_audio(wav)
# 		wavfile.write("../data/test_original.wav", cfg.sampling_rate, wav)
		wav = wav.astype(np.float32) / np.iinfo(np.int16).max
		
# 		# be aware, some files are shorter than 1 sec!
# 		if len(wav) < cfg.sampling_rate:
# 			continue
		if is_normalization:
			wav = standardization(wav)
		
# 		print feat.shape

# 		# we want to compute spectograms by means of short time fourier transform:
# 		specgram = signal.stft(
# 			wav,
# 			400,  # 16000 [samples per second] * 0.025 [s] -- default stft window frame
# 			160,  # 16000 * 0.010 -- default stride
# 		)
		
		

		#sampling rate means 1sec long data
		L = cfg.sampling_rate
		# let's generate more silence!
		samples_per_file = 1 if label_id != cfg.n2i(cfg.sil_flg) else resampline_sil_rate
		for _ in range(samples_per_file):
			if len(wav) > L:
				beg = np.random.randint(0, len(wav) - L)
# 				print len(wav)
			else:
				beg = 0
			wav = wav[beg: beg + L]
			x.append(wav)
			y.append(np.int32(label_id))
	y = to_categorical(y, num_classes = cfg.CLS_NUM)
	return x, y


def get_features(data, name, sampling_rate):
	
	print "call {}() func".format(name)
	output = map(lambda x : eval(name)(x, sampling_rate), data)
	
	return output


def pad_data(data):
	lengths = map(lambda x : len(x), data)
	L = max(lengths)
	npz_data = np.zeros((len(data), L, data[0].shape[1]))
	for i, x in enumerate(data):
		pad_x = x
		if len(x) > L:
			print "found overlength item!"
		for j in range(len(x), L):
			pad_x = np.row_stack(x, np.ones(x.shape[1]) * cfg.non_flg_index)
		npz_data[i] = pad_x
	return npz_data

def make_file_name(head, type, *args):
	return head + make_file_trim(type, args)
		
def gen_train_feature(name, is_normalization=True, down_rate=1.0, data_dir="../data/"):
	train, val = load_data(data_dir)
	sampling_rate = int(cfg.sampling_rate * down_rate)
	x, y = get_wav(train, is_normalization=is_normalization)
	if down_rate < 1.0:
		x = down_sample(x, down_rate)
# 	x = pad_data(x)
	
	x = get_features(x, name, sampling_rate)
	

	
	v_x, v_y = get_wav(val)
# 	v_x = pad_data(v_x)
	if down_rate < 1.0:
		v_x = down_sample(v_x, down_rate)
	v_x = get_features(v_x, name, sampling_rate)
	
	
	np.savez(make_file_name("../data/train/train", "npz", sampling_rate, name), x = x, y = y)
	np.savez(make_file_name("../data/valid/valid", "npz", sampling_rate, name), x = v_x, y = v_y)
	print "sampling rate:{}".format(sampling_rate)
	print "feature shape:{}*{}".format(x[0].shape[0], x[0].shape[1])
	print "completed gen training data..."
	
def gen_test_feature(name, is_normalization=True, down_rate=1.0, data_dir="../data/test/"):
	paths = gen_input_paths(data_dir + "audio/", ".wav")
	print "test data num:{}".format(len(paths))
	x = []
	sampling_rate = int(cfg.sampling_rate * down_rate)
	for i,fname in enumerate(paths):
		_, wav = wavfile.read(fname)
		wav = wav.astype(np.float32) / np.iinfo(np.int16).max
		if is_normalization:
			wav = standardization(wav)
		L = cfg.sampling_rate

		if len(wav) > L:
			beg = np.random.randint(0, len(wav) - L)
		else:
			beg = 0
		wav = wav[beg: beg + L]

		x.append(wav)
		if i % 10000 == 0:
			print "read {} files".format(i)
	print "completed read wav files, start extracting fearures..."
	if down_rate < 1.0:
		x = down_sample(x, down_rate)
	x = get_features(x, name, sampling_rate)
	
	np.savez(make_file_name(data_dir + "test", "npz", sampling_rate, name), x = x)
	print "sampling rate:{}".format(sampling_rate)
	print "feature shape:{}*{}".format(x[0].shape[0], x[0].shape[1])
	print "completed gen test data..."
	
def get_test_data_from_files(root_path="../data/test/", filter_trim=None):
	trim = get_file_trim(filter_trim = filter_trim)
	print "process file type:" + trim
	paths = gen_input_paths(root_path, trim)
	x_list = []

	
	print "We'll load {} files...".format(len(paths))
	for path in paths:
		print "load data from:" + path
		data = np.load(path)
		x_list.append(data['x'])
		
	
	x = np.vstack(x_list)
	

	return x

def gen_input_paths(root_path="../data/ext/", file_ext_name=".csv"):
	list_path = os.listdir(root_path)
	
# 	total_num = 0
	paths = []
	for path in list_path:
		file_path = os.path.join(root_path, path)
		if os.path.isfile(file_path) and file_path.endswith(file_ext_name):
			paths.append(file_path)
# 	paths.append('../data/en_train.csv')
	
	return paths
def get_file_trim(type="npz", filter_trim=None):
	return ".{}".format(type) if (filter_trim == "") or (filter_trim is None) else "_{}.{}".format(filter_trim, type)

def make_file_trim(type="npz", *args):
	name = ".{}".format(type)
	if args is not None and len(args) > 0:
		for arg in args[0]:
			name = "_" + str(arg) + name
	
	return name
	
	
def get_training_data_from_files(root_path, filter_trim=None):
	trim = get_file_trim(filter_trim = filter_trim)
	print "process file type:" + trim
	paths = gen_input_paths(root_path, trim)
	x_list = []
	y_list = []
	
	print "We'll load {} files...".format(len(paths))
	for path in paths:
		print "load data from:" + path
		data = np.load(path)
		x_list.append(data['x'])
		y_list.append(data['y'])
		
	
	x = np.vstack(x_list)
	y = np.vstack(y_list)
	

	return x, y

def load_data_ext(data_dir, default_label):
	paths = gen_input_paths(data_dir, ".wav")
	samples = []
	for path in paths:
		index = path.find('-')
		label = default_label
		if index > -1:
			label = path[index + 1:-4]
			if label not in cfg.POSSIBLE_LABELS:
				label = cfg.unk_flg
		samples.append((cfg.n2i(label), path))
		
	return samples		

def gen_ext_feature(id, name, is_normalization, down_rate=1.0, default_label=cfg.sil_flg):
	data_dir = "../data/train/ext{}/".format(id)
# 	output = "../data/train/train_ext{}_{}.npz".format(id, name)
	
	sampling_rate = int(cfg.sampling_rate * down_rate)
	output = make_file_name("../data/train/train_ext{}".format(id), "npz", sampling_rate, name)
	samples = load_data_ext(data_dir, default_label)			
	x, y = get_wav(samples, resampline_sil_rate=1, is_normalization=is_normalization)
	if down_rate < 1.0:
		x = down_sample(x, down_rate)
	x = get_features(x, name, sampling_rate)
	x = pad_data(x)
	np.savez(output, x = x, y = y)
	print "sampling rate:{}".format(sampling_rate)
	print "feature shape:{}*{}".format(x[0].shape[0], x[0].shape[1])
	print "completed gen ext \"{}\" feature of {} files from ext{}.".format(default_label, x.shape[0], id)

def init_noise_array(paths):
	
	data = []
	for path in paths:
		wpaths = gen_input_paths(path, ".wav")
		for fname in wpaths:
			if '-' not in fname:
				_, wav = wavfile.read(fname)
				wav = wav.astype(np.float32) / np.iinfo(np.int16).max
				
				# be aware, some files are shorter than 1 sec!
				if len(wav) < cfg.sampling_rate:
					continue
				N = len(wav) / cfg.sampling_rate
				for i in range(N):
					data.append(wav[i*cfg.sampling_rate:(i+1)*cfg.sampling_rate])
	print "build up {} items' noise set.".format(len(data))
	return data

noise_array = init_noise_array(['../data/train/audio/_background_noise_',"../data/train/ext1/", "../data/train/ext2/"])
	


def mix_noise(data, rate=0.005):
# 	L = data.shape[-1]
	axis = len(data.shape) - 1
	num = 1 if axis <= 0 else data.shape[0]
	noises = None
	if num > 1:
		noises = np.vstack(random.sample(noise_array, num))
	else:
		noises = random.sample(noise_array, num)[0]
	return data + noises * rate
	
def shift(data, rate=0.1):
	'''
	shift wav data, if rate > 0, the data sequence will be shift right rate*len(data), 
	or else will be shift left
	'''
	L = data.shape[-1]
	offset = int(L * rate)
	
	return np.roll(data, offset, axis=len(data.shape) - 1)


def stretch(data, rate=1.0, input_length=cfg.sampling_rate):
	'''
	stretching wav data, if rate > 1, the frequency will higher than before, else lower than before
	'''
	data = librosa.effects.time_stretch(data, rate)
	if len(data)>input_length:
		data = data[:input_length]
	else:
		data = np.pad(data, (0, max(0, input_length - len(data))), "constant")
	
	return data

def down_sample(data, rate=0.5):
	return map(lambda x : signal.resample(x, int(cfg.sampling_rate * rate)), data)

def random_call(data, ops):
	
	out = data
	for op in ops:
		name = op[0]
		
		val = random.uniform(0, 1)
		if val < op[1]:
			rate = random.uniform(op[2][0], op[2][1])
			out = eval(name)(out, rate)
	return out

def augmentation(data, outdir='../data/train/ext8/', ops=[("mix_noise", 0.85, (1.0, 3.0)), ("shift", 0.8, (-0.15, 0.15)), ("stretch", 0.75, (0.75, 1.35))]):
	
	cnt = 1
	for (label_id, fname) in data:
# 		print fname
		_, wav = wavfile.read(fname)
		if len(wav) > cfg.sampling_rate:
			print "skip overlength file {}".format(fname)
			continue
		wav = pad_audio(wav)
		wav = wav.astype(np.float64)
		wav = random_call(wav, ops)
		fname = os.path.basename(fname)
		index = fname.find(".wav")
		if "-" not in fname:
			fname_out = fname[0:index] + "-" + cfg.i2n(label_id) + ".wav"
			fname_out = outdir + fname_out
			wav = wav.astype(np.int16)
			
			id = 1
			while os.path.exists(fname_out):
				fname_out = fname[0:index] + "_" + str(id) +"-" + cfg.i2n(label_id) + ".wav"
				fname_out = outdir + fname_out
				id += 1
				print id
				
			wavfile.write(fname_out, cfg.sampling_rate, wav)
			print "processed num:{}".format(cnt)
			cnt += 1

def gen_augmentation_data():
	train, _ = load_data()
	augmentation(train)
	
def test():
	#name should in ["mfcc", "logfbank", "logspecgram"]
# 	func = logfbank
# 	print make_file_name("../data/train/train", "npz", 16000, "logspecgram")
	name = "logspecgram"
	is_normalization = True
	down_rate=0.5
# 	gen_augmentation_data()
# 	default_label = 'off'
	gen_train_feature(name, is_normalization, down_rate)
	gen_test_feature(name, is_normalization, down_rate)
# 	gen_ext_feature(0, name, is_normalization, down_rate, cfg.sil_flg)
	gen_ext_feature(1, name, is_normalization, down_rate, cfg.sil_flg)
	gen_ext_feature(2, name, is_normalization, down_rate, cfg.sil_flg)
	gen_ext_feature(3, name, is_normalization, down_rate, 'off')
	gen_ext_feature(4, name, is_normalization, down_rate, 'no')
	gen_ext_feature(5, name, is_normalization, down_rate, 'up')
	gen_ext_feature(6, name, is_normalization, down_rate, 'stop')
	gen_ext_feature(7, name, is_normalization, down_rate, 'unknown')
if __name__ == "__main__":
	test()