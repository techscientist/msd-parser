import os
import re
import json
import glob
import hdf5_getters
import time
import numpy as np

''' some "static" data used in conjunction with the helper methods ''' 

#each 12-element vector corresponds to the 12 pitches, starting with C natural and going up to B natural

CHORD_TEMPLATE_MAJOR = [[1,0,0,0,1,0,0,1,0,0,0,0],[0,1,0,0,0,1,0,0,1,0,0,0],[0,0,1,0,0,0,1,0,0,1,0,0],[0,0,0,1,0,0,0,1,0,0,1,0],[0,0,0,0,1,0,0,0,1,0,0,1],[1,0,0,0,0,1,0,0,0,1,0,0],[0,1,0,0,0,0,1,0,0,0,1,0],[0,0,1,0,0,0,0,1,0,0,0,1],[1,0,0,1,0,0,0,0,1,0,0,0],[0,1,0,0,1,0,0,0,0,1,0,0],[0,0,1,0,0,1,0,0,0,0,1,0],[0,0,0,1,0,0,1,0,0,0,0,1]]
CHORD_TEMPLATE_MINOR =[[1,0,0,1,0,0,0,1,0,0,0,0],[0,1,0,0,1,0,0,0,1,0,0,0],[0,0,1,0,0,1,0,0,0,1,0,0],[0,0,0,1,0,0,1,0,0,0,1,0],[0,0,0,0,1,0,0,1,0,0,0,1],[1,0,0,0,0,1,0,0,1,0,0,0],[0,1,0,0,0,0,1,0,0,1,0,0],[0,0,1,0,0,0,0,1,0,0,1,0],[0,0,0,1,0,0,0,0,1,0,0,1],[1,0,0,0,1,0,0,0,0,1,0,0],[0,1,0,0,0,1,0,0,0,0,1,0],[0,0,1,0,0,0,1,0,0,0,0,1]]
CHORD_TEMPLATE_DOM7 = [[1,0,0,0,1,0,0,1,0,0,1,0],[0,1,0,0,0,1,0,0,1,0,0,1],[1,0,1,0,0,0,1,0,0,1,0,0],[0,1,0,1,0,0,0,1,0,0,1,0],[0,0,1,0,1,0,0,0,1,0,0,1],[1,0,0,1,0,1,0,0,0,1,0,0],[0,1,0,0,1,0,1,0,0,0,1,0],[0,0,1,0,0,1,0,1,0,0,0,1],[1,0,0,1,0,0,1,0,1,0,0,0],[0,1,0,0,1,0,0,1,0,1,0,0],[0,0,1,0,0,1,0,0,1,0,1,0],[0,0,0,1,0,0,1,0,0,1,0,1]]
CHORD_TEMPLATE_MIN7 = [[1,0,0,1,0,0,0,1,0,0,1,0],[0,1,0,0,1,0,0,0,1,0,0,1],[1,0,1,0,0,1,0,0,0,1,0,0],[0,1,0,1,0,0,1,0,0,0,1,0],[0,0,1,0,1,0,0,1,0,0,0,1],[1,0,0,1,0,1,0,0,1,0,0,0],[0,1,0,0,1,0,1,0,0,1,0,0],[0,0,1,0,0,1,0,1,0,0,1,0],[0,0,0,1,0,0,1,0,1,0,0,1],[1,0,0,0,1,0,0,1,0,1,0,0],[0,1,0,0,0,1,0,0,1,0,1,0],[0,0,1,0,0,0,1,0,0,1,0,1]]

CHORD_TEMPLATE_MAJOR_means = [np.mean(chord) for chord in CHORD_TEMPLATE_MAJOR]
CHORD_TEMPLATE_MINOR_means = [np.mean(chord) for chord in CHORD_TEMPLATE_MINOR]
CHORD_TEMPLATE_DOM7_means = [np.mean(chord) for chord in CHORD_TEMPLATE_DOM7]
CHORD_TEMPLATE_MIN7_means = [np.mean(chord) for chord in CHORD_TEMPLATE_MIN7]

CHORD_TEMPLATE_MAJOR_stdevs = [np.std(chord) for chord in CHORD_TEMPLATE_MAJOR]
CHORD_TEMPLATE_MINOR_stdevs = [np.std(chord) for chord in CHORD_TEMPLATE_MINOR]
CHORD_TEMPLATE_DOM7_stdevs = [np.std(chord) for chord in CHORD_TEMPLATE_DOM7]
CHORD_TEMPLATE_MIN7_stdevs = [np.std(chord) for chord in CHORD_TEMPLATE_MIN7]

TIMBRE_CLUSTERS = [[  1.38679881e-01,   3.95702571e-02,   2.65410235e-02,
          7.38301998e-03,  -1.75014636e-02,  -5.51147732e-02,
          8.71851698e-03,  -1.17595855e-02,   1.07227900e-02,
          8.75951680e-03,   5.40391877e-03,   6.17638908e-03],
       [  3.14344510e+00,   1.17405599e-01,   4.08053561e+00,
         -1.77934450e+00,   2.93367968e+00,  -1.35597928e+00,
         -1.55129489e+00,   7.75743158e-01,   6.42796685e-01,
          1.40794256e-01,   3.37716831e-01,  -3.27103815e-01],
       [  3.56548165e-01,   2.73288705e+00,   1.94355982e+00,
          1.06892477e+00,   9.89739475e-01,  -8.97330631e-02,
          8.73234495e-01,  -2.00747009e-03,   3.44488367e-01,
          9.93117800e-02,  -2.43471766e-01,  -1.90521726e-01],
       [  4.22442037e-01,   4.14115783e-01,   1.43926557e-01,
         -1.16143322e-01,  -5.95186216e-02,  -2.36927188e-01,
         -6.83151409e-02,   9.86816882e-02,   2.43219098e-02,
          6.93558977e-02,   6.80121418e-03,   3.97485360e-02],
       [  1.94727799e-01,  -1.39027782e+00,  -2.39875671e-01,
         -2.84583677e-01,   1.92334219e-01,  -2.83421048e-01,
          2.15787541e-01,   1.14840341e-01,  -2.15631833e-01,
         -4.09496877e-02,  -6.90838017e-03,  -7.24394810e-03],
       [  1.96565167e-01,   4.98702717e-02,  -3.43697282e-01,
          2.54170701e-01,   1.12441266e-02,   1.54740401e-01,
         -4.70447408e-02,   8.10868802e-02,   3.03736697e-03,
          1.43974944e-03,  -2.75044913e-02,   1.48634678e-02],
       [  2.21364497e-01,  -2.96205105e-01,   1.57754028e-01,
         -5.57641279e-02,  -9.25625566e-02,  -6.15316168e-02,
         -1.38139882e-01,  -5.54936599e-02,   1.66886836e-01,
          6.46238260e-02,   1.24093863e-02,  -2.09274345e-02],
       [  2.12823455e-01,  -9.32652720e-02,  -4.39611467e-01,
         -2.02814479e-01,   4.98638770e-02,  -1.26572488e-01,
         -1.11181799e-01,   3.25075635e-02,   2.01416694e-02,
         -5.69216463e-02,   2.61922912e-02,   8.30817468e-02],
       [  1.62304042e-01,  -7.34813956e-03,  -2.02552550e-01,
          1.80106705e-01,  -5.72110826e-02,  -9.17148244e-02,
         -6.20429191e-03,  -6.08892354e-02,   1.02883628e-02,
          3.84878478e-02,  -8.72920419e-03,   2.37291230e-02],
       [  1.69023095e-01,   6.81311168e-02,  -3.71039856e-02,
         -2.13139780e-02,  -4.18752028e-03,   1.36407740e-01,
          2.58515825e-02,  -4.10328777e-04,   2.93149920e-02,
         -1.97874734e-02,   2.01177066e-02,   4.29260690e-03],
       [  4.16829358e-01,  -1.28384095e+00,   8.86081556e-01,
          9.13717416e-02,  -3.19420208e-01,  -1.82003637e-01,
         -3.19865507e-02,  -1.71517045e-02,   3.47472066e-02,
         -3.53047665e-02,   5.58354602e-02,  -5.06222122e-02],
       [  3.83948137e-01,   1.06020034e-01,   4.01191058e-01,
          1.49470482e-01,  -9.58422411e-02,  -4.94473336e-02,
          2.27589858e-02,  -5.67352733e-02,   3.84666644e-02,
         -2.15828055e-02,  -1.67817151e-02,   1.15426241e-01],
       [  9.07946444e-01,   3.26120397e+00,   2.98472002e+00,
         -1.42615404e-01,   1.29886103e+00,  -4.53380431e-01,
          1.54008478e-01,  -3.55297093e-02,  -2.95809181e-01,
          1.57037690e-01,  -7.29692046e-02,   1.15180285e-01],
       [  1.60870896e+00,  -2.32038235e+00,  -7.96211044e-01,
          1.55058968e+00,  -2.19377663e+00,   5.01030526e-01,
         -1.71767279e+00,  -1.36642470e+00,  -2.42837527e-01,
         -4.14275615e-01,  -7.33148530e-01,  -4.56676578e-01],
       [  6.42870687e-01,   1.34486839e+00,   2.16026845e-01,
         -2.13180345e-01,   3.10866747e-01,  -3.97754955e-01,
         -3.54439151e-01,  -5.95938041e-04,   4.95054274e-03,
          4.67013422e-02,  -1.80823854e-02,   1.25808320e-01],
       [  1.16780496e+00,   2.28141229e+00,  -3.29418720e+00,
         -1.54239912e+00,   2.12372153e-01,   2.51116768e+00,
          1.84273560e+00,  -4.06183916e-01,   1.19175125e+00,
         -9.24407446e-01,   6.85444429e-01,  -6.38729005e-01],
       [  2.39097414e-01,  -1.13382447e-02,   3.06327342e-01,
          4.68182987e-03,  -1.03107607e-01,  -3.17661969e-02,
          3.46533705e-02,   1.46440386e-02,   6.88291154e-02,
          1.72580481e-02,  -6.23970238e-03,  -6.52822380e-03],
       [  1.74850329e-01,  -1.86077411e-01,   2.69285838e-01,
          5.22452803e-02,  -3.71708289e-02,  -6.42874319e-02,
         -5.01920042e-03,  -1.14565540e-02,  -2.61300268e-03,
         -6.94872458e-03,   1.20157063e-02,   2.01341977e-02],
       [  1.93220674e-01,   1.62738332e-01,   1.72794061e-02,
          7.89933755e-02,   1.58494767e-01,   9.04541006e-04,
         -3.33177052e-02,  -1.42411500e-01,  -1.90471155e-02,
         -2.41622739e-02,  -2.57382438e-02,   2.84895062e-02],
       [  3.31179197e+00,  -1.56765268e-01,   4.42446188e+00,
          2.05496297e+00,   5.07031622e+00,  -3.52663849e-02,
         -5.68337901e+00,  -1.17825301e+00,   5.41756637e-01,
         -3.15541339e-02,  -1.58404846e+00,   7.37887234e-01],
       [  2.36033237e-01,  -5.01380019e-01,  -7.01568834e-02,
         -2.14474169e-01,   5.58739133e-01,  -3.45340886e-01,
          2.36469930e-01,  -2.51770230e-02,  -4.41670143e-01,
         -1.73364633e-01,   9.92353986e-03,   1.01775476e-01],
       [  3.13672832e+00,   1.55128891e+00,   4.60139512e+00,
          9.82477544e-01,  -3.87108002e-01,  -1.34239667e+00,
         -3.00065797e+00,  -4.41556909e-01,  -7.77546208e-01,
         -6.59017029e-01,  -1.42596356e-01,  -9.78935498e-01],
       [  8.50714148e-01,   2.28658856e-01,  -3.65260753e+00,
          2.70626948e+00,  -1.90441544e-01,   5.66625676e+00,
          1.77531510e+00,   2.39978921e+00,   1.10965660e+00,
          1.58484130e+00,  -1.51579214e-02,   8.64324026e-01],
       [  1.14302559e+00,   1.18602811e+00,  -3.88130412e+00,
          8.69833825e-01,  -8.23003310e-01,  -4.23867795e-01,
          8.56022598e-01,  -1.08015106e+00,   1.74840192e-01,
         -1.35493558e-02,  -1.17012561e+00,   1.68572940e-01],
       [  3.54117814e+00,   6.12714769e-01,   7.67585243e+00,
          2.50391333e+00,   1.81374399e+00,  -1.46363231e+00,
         -1.74027236e+00,  -5.72924078e-01,  -1.20787368e+00,
         -4.13954661e-01,  -4.62561948e-01,   6.78297871e-01],
       [  8.31843044e-01,   4.41635485e-01,   7.00724425e-02,
         -4.72159900e-02,   3.08326493e-01,  -4.47009822e-01,
          3.27806057e-01,   6.52370380e-01,   3.28490360e-01,
          1.28628172e-01,  -7.78065861e-02,   6.91343399e-02],
       [  4.90082031e-01,  -9.53180204e-01,   1.76970476e-01,
          1.57256960e-01,  -5.26196238e-02,  -3.19264458e-01,
          3.91808304e-01,   2.19368239e-01,  -2.06483291e-01,
         -6.25044005e-02,  -1.05547224e-01,   3.18934196e-01],
       [  1.49899454e+00,  -4.30708817e-01,   2.43770498e+00,
          7.03149621e-01,  -2.28827845e+00,   2.70195855e+00,
         -4.71484280e+00,  -1.18700075e+00,  -1.77431396e+00,
         -2.23190236e+00,   8.20855264e-01,  -2.35859902e-01],
       [  1.20322544e-01,  -3.66300816e-01,  -1.25699953e-01,
         -1.21914056e-01,   6.93277338e-02,  -1.31034684e-01,
         -1.54955924e-03,   2.48094288e-02,  -3.09576314e-02,
         -1.66369415e-03,   1.48904987e-04,  -1.42151992e-02],
       [  6.52394765e-01,  -6.81024464e-01,   6.36868117e-01,
          3.04950208e-01,   2.62178992e-01,  -3.20457080e-01,
         -1.98576098e-01,  -3.02173163e-01,   2.04399765e-01,
          4.44513847e-02,  -9.50111498e-02,  -1.14198739e-02],
       [  2.06762180e-01,  -2.08101829e-01,   2.61977630e-01,
         -1.71672300e-01,   5.61794250e-02,   2.13660185e-01,
          3.90259585e-02,   4.78176392e-02,   1.72812607e-02,
          3.44052067e-02,   6.26899067e-03,   2.48544728e-02],
       [  7.39717363e-01,   4.37786285e+00,   2.54995502e+00,
          1.13151212e+00,  -3.58509503e-01,   2.20806129e-01,
         -2.20500355e-01,  -7.22409824e-02,  -2.70534083e-01,
          1.07942098e-03,   2.70174668e-01,   1.87279353e-01],
       [  1.25593809e+00,   6.71054880e-02,   8.70352571e-01,
         -4.32607959e+00,   2.30652217e+00,   5.47476105e+00,
         -6.11052479e-01,   1.07955720e+00,  -2.16225471e+00,
         -7.95770149e-01,  -7.31804973e-01,   9.68935954e-01],
       [  1.17233757e-01,  -1.23897829e-01,  -4.88625265e-01,
          1.42036530e-01,  -7.23286756e-02,  -6.99808763e-02,
         -1.17525019e-02,   5.70221674e-02,  -7.67796123e-03,
          4.17505873e-02,  -2.33375716e-02,   1.94121001e-02],
       [  1.67511025e+00,  -2.75436700e+00,   1.45345593e+00,
          1.32408871e+00,  -1.66172505e+00,   1.00560074e+00,
         -8.82308160e-01,  -5.95708043e-01,  -7.27283590e-01,
         -1.03975499e+00,  -1.86653334e-02,   1.39449745e+00],
       [  3.20587677e+00,  -2.84451104e+00,   8.54849957e+00,
         -4.44001235e-01,   1.04202144e+00,   7.35333682e-01,
         -2.48763292e+00,   7.38931361e-01,  -1.74185596e+00,
         -1.07581842e+00,   2.05759299e-01,  -8.20483513e-01],
       [  3.31279737e+00,  -5.08655734e-01,   6.61530870e+00,
          1.16518280e+00,   4.74499155e+00,  -2.31536191e+00,
         -1.34016130e+00,  -7.15381712e-01,   2.78890594e+00,
          2.04189275e+00,  -3.80003033e-01,   1.16034914e+00],
       [  1.79522019e+00,  -8.13534697e-02,   4.37167420e-01,
          2.26517020e+00,   8.85377295e-01,   1.07481514e+00,
         -7.25322296e-01,  -2.19309506e+00,  -7.59468916e-01,
         -1.37191387e+00,   2.60097913e-01,   9.34596450e-01],
       [  3.50400906e-01,   8.17891485e-01,  -8.63487084e-01,
         -7.31760701e-01,   9.70320805e-02,  -3.60023996e-01,
         -2.91753495e-01,  -8.03073817e-02,   6.65930095e-02,
          1.60093340e-01,  -1.29158086e-01,  -5.18806100e-02],
       [  2.25922929e-01,   2.78461593e-01,   5.39661393e-02,
         -2.37662670e-02,  -2.70343295e-02,  -1.23485570e-01,
          2.31027499e-03,   5.87465112e-05,   1.86127188e-02,
          2.83074747e-02,  -1.87198676e-04,   1.24761782e-02],
       [  4.53615634e-01,   3.18976020e+00,  -8.35029351e-01,
          7.84124578e+00,  -4.43906795e-01,  -1.78945492e+00,
         -1.14521031e+00,   1.00044304e+00,  -4.04084981e-01,
         -4.86030348e-01,   1.05412721e-01,   5.63666445e-02],
       [  3.93714086e-01,  -3.07226477e-01,  -4.87366619e-01,
         -4.57481697e-01,  -2.91133171e-04,  -2.39881719e-01,
         -2.15591352e-01,  -1.21332941e-01,   1.42245002e-01,
          5.02984582e-02,  -8.05878851e-03,   1.95534173e-01],
       [  1.86913010e-01,  -1.61000977e-01,   5.95612425e-01,
          1.87804293e-01,   2.22064227e-01,  -1.09008289e-01,
          7.83845058e-02,   5.15228647e-02,  -8.18113578e-02,
         -2.37860551e-02,   3.41013800e-03,   3.64680417e-02],
       [  3.32919314e+00,  -2.14341251e+00,   7.20913997e+00,
          1.76143734e+00,   1.64091808e+00,  -2.66887649e+00,
         -9.26748006e-01,  -2.78599285e-01,  -7.39434005e-01,
         -3.87363085e-01,   8.00557250e-01,   1.15628886e+00],
       [  4.76496444e-01,  -1.19334793e-01,   3.09037235e-01,
         -3.45545294e-01,   1.30114716e-01,   5.06895559e-01,
          2.12176840e-01,  -4.14296750e-03,   4.52439064e-02,
         -1.62163990e-02,   6.93683152e-02,  -5.77607592e-03],
       [  3.00019324e-01,   5.43432074e-02,  -7.72732930e-01,
          1.47263806e+00,  -2.79012581e-02,  -2.47864869e-01,
         -2.10011388e-01,   2.78202425e-01,   6.16957205e-02,
         -1.66924986e-01,  -1.80102286e-01,  -3.78872162e-03]]

TIMBRE_MEANS = [np.mean(t) for t in TIMBRE_CLUSTERS]
TIMBRE_STDEVS = [np.std(t) for t in TIMBRE_CLUSTERS]

'''helper methods to process raw msd data'''

def normalize_pitches(h5):
	key = int(hdf5_getters.get_key(h5))
	segments_pitches = hdf5_getters.get_segments_pitches(h5)
	segments_pitches_new = [transpose_by_key(pitch_seg,key) for pitch_seg in segments_pitches]
	return segments_pitches_new

def transpose_by_key(pitch_seg,key):
	pitch_seg_new = []
	for i in range(0,12):
		idx = (i + key) % 12
		pitch_seg_new.append(pitch_seg[idx])
	return pitch_seg_new

''' given a time segment with distributions of the 12 pitches, find the most likely chord played'''
def find_most_likely_chord(pitch_vector):
	rho_max = 0.0;
	# index each chord
	most_likely_chord = (1,1)
	for idx, (chord,mean,stdev) in enumerate(zip(CHORD_TEMPLATE_MAJOR,CHORD_TEMPLATE_MAJOR_means,CHORD_TEMPLATE_MAJOR_stdevs)):
		rho = 0.0
		for i in range(0,12):
			rho += (chord[i] - mean)*(pitch_vector[i] - np.mean(pitch_vector))/((stdev+0.01)*(np.std(pitch_vector)+0.01))
		if (abs(rho) > abs(rho_max)):
			rho_max = rho
			most_likely_chord = (1,idx)
	for idx, (chord,mean,stdev) in enumerate(zip(CHORD_TEMPLATE_MINOR,CHORD_TEMPLATE_MINOR_means,CHORD_TEMPLATE_MINOR_stdevs)):
		rho = 0.0
		for i in range(0,12):
			rho += (chord[i] - mean)*(pitch_vector[i] - np.mean(pitch_vector))/((stdev+0.01)*(np.std(pitch_vector)+0.01))	
		if (abs(rho) > abs(rho_max)):	
			rho_max = rho
			most_likely_chord = (2,idx)
	for idx, (chord,mean,stdev) in enumerate(zip(CHORD_TEMPLATE_DOM7,CHORD_TEMPLATE_DOM7_means,CHORD_TEMPLATE_DOM7_stdevs)):
		rho = 0.0
		for i in range(0,12):
			rho += (chord[i] - mean)*(pitch_vector[i] - np.mean(pitch_vector))/((stdev+0.01)*(np.std(pitch_vector)+0.01))
		if (abs(rho) > abs(rho_max)):	
			rho_max = rho
			most_likely_chord = (3,idx)
	for idx, (chord,mean,stdev) in enumerate(zip(CHORD_TEMPLATE_MIN7,CHORD_TEMPLATE_MIN7_means,CHORD_TEMPLATE_MIN7_stdevs)):
		rho = 0.0
		for i in range(0,12):
			rho += (chord[i] - mean)*(pitch_vector[i] - np.mean(pitch_vector))/((stdev+0.01)*(np.std(pitch_vector)+0.01))	
		if (abs(rho) > abs(rho_max)):	
			rho_max = rho
			most_likely_chord = (4,idx)
	return most_likely_chord

def find_most_likely_timbre_category(timbre_vector):
	most_likely_timbre_cat = 0
	rho_max = 0.0
	for idx, (seg,mean,stdev) in enumerate(zip(TIMBRE_CLUSTERS,TIMBRE_MEANS,TIMBRE_STDEVS)):
		rho = 0.0
		for i in range(0,12):
			rho += (seg[i] - mean)*(timbre_vector[i] - np.mean(seg))/((stdev+0.01)*(np.std(timbre_vector)+0.01))
		if (abs(rho) > abs(rho_max)):
			rho_max = rho
			most_likely_timbre_cat = idx
	return most_likely_timbre_cat

'''
timbre_data = []
# f = './../../scratch/network/mssilver/mssilver/timbre_frames_all.txt'
f = 'timbre_frames_all.txt'
with open(f,'r') as t:
	timbre_data = json.loads(list(t)[0])

for t in timbre_data:
	print str(find_most_likely_timbre_category(t))
'''
