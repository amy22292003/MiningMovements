"""
cmeans.py : Fuzzy C-means clustering algorithm.

"""
import numpy as np
from scipy.spatial.distance import cdist
#from .distance import cdist


def _cmeans0(data1, data2, u_old, c, w, m):
	"""
	Single step in generic fuzzy c-means clustering algorithm. Modified from
	Ross, Fuzzy Logic w/Engineering Applications (2010) p.352-353, equations
	10.28 - 10.35.

	Parameters inherited from cmeans()

	"""
	# Normalizing, then eliminating any potential zero values.
	u_old /= np.ones((c, 1)).dot(np.atleast_2d(u_old.sum(axis=0)))
	u_old = np.fmax(u_old, np.finfo(np.float64).eps)

	um = u_old ** m

	# Calculate cluster centers
	data1 = data1.T
	cntr1 = um.dot(data1) / (np.ones((data1.shape[1],
									1)).dot(np.atleast_2d(um.sum(axis=1))).T)

	data2 = data2.T
	cntr2 = um.dot(data2) / (np.ones((data2.shape[1],
									1)).dot(np.atleast_2d(um.sum(axis=1))).T)


	d1 = _distance(data1, cntr1)
	max1 = np.amax(d1)
	d2 = _distance(data2, cntr2)
	max2 = np.amax(d2)

	# convert distance to similarity
	d1 = d1 / max1
	d2 = d2 / max2
	d = w * d1 + (1-w) * (1-d2)
	print("-- d1:", d1[0][0:5], " \n  ,d2:", d2[0][0:5], " \n  ,d:", d[0][0:5])
	print("   std 1:", np.std(d1), " ,2:", np.std(d2), " ,d:", np.std(d))

	d = np.fmax(d, np.finfo(np.float64).eps)

	jm = (um * d ** 2).sum()

	u = d ** (- 2. / (m - 1))
	u /= np.ones((c, 1)).dot(np.atleast_2d(u.sum(axis=0)))
	return cntr1, cntr2, u, jm, d1, d2, d

def _distance(data, centers):
	"""
	Calcuate Euclidean distance from each point to each cluster center,
	returning results in matrix form.

	Parameters
	----------
	data : 2d array (N x Q)
		Data to be analyzed. There are N data points.
	centers : 2d array (C x Q)
		Cluster centers. There are C clusters, with Q features.

	Returns
	-------
	dist : 2d array (C x N)
		Euclidean distance from each point, to each cluster center.

	See Also
	--------
	scipy.spatial.distance.cdist

	"""
	return cdist(data, centers).T


def _fp_coeff(u):
	"""
	Fuzzy partition coefficient `fpc` relative to fuzzy c-partitioned
	matrix u. Measures 'fuzziness' in partitioned clustering.

	Parameters
	----------
	u : 2d array (C, N)
		Fuzzy c-partitioned matrix; N = number of data points and C = number
		of clusters.

	Returns
	-------
	fpc : float
		Fuzzy partition coefficient.

	"""
	n = u.shape[1]

	return np.trace(u.dot(u.T)) / float(n)


def cmeans(data1, data2, c, w, m, error, maxiter, init=None, seed=None):
	"""
	Fuzzy c-means clustering algorithm [1]_.

	Parameters
	----------
	data : 2d array, size (S, N)
		Data to be clustered.  N is the number of data sets; S is the number
		of features within each sample vector.
	c : int
		Desired number of clusters or classes.
	m : float
		Array exponentiation applied to the membership function u_old at each
		iteration, where U_new = u_old ** m.
	error : float
		Stopping criterion; stop early if the norm of (u[p] - u[p-1]) < error.
	maxiter : int
		Maximum number of iterations allowed.
	init : 2d array, size (S, N)
		Initial fuzzy c-partitioned matrix. If none provided, algorithm is
		randomly initialized.
	seed : int
		If provided, sets random seed of init. No effect if init is
		provided. Mainly for debug/testing purposes.

	Returns
	-------
	cntr : 2d array, size (S, c)
		Cluster centers.  Data for each center along each feature provided
		for every cluster (of the `c` requested clusters).
	u : 2d array, (S, N)
		Final fuzzy c-partitioned matrix.
	u0 : 2d array, (S, N)
		Initial guess at fuzzy c-partitioned matrix (either provided init or
		random guess used if init was not provided).
	d : 2d array, (S, N)
		Final Euclidian distance matrix.
	jm : 1d array, length P
		Objective function history.
	p : int
		Number of iterations run.
	fpc : float
		Final fuzzy partition coefficient.


	Notes
	-----
	The algorithm implemented is from Ross et al. [1]_.

	References
	----------
	.. [1] Ross, Timothy J. Fuzzy Logic With Engineering Applications, 3rd ed.
		   Wiley. 2010. ISBN 978-0-470-74376-8 pp 352-353, eq 10.28 - 10.35.

	"""
	# Setup u0
	if init is None:
		if seed is not None:
			np.random.seed(seed=seed)
		n = data1.shape[1]
		u0 = np.random.rand(c, n)
		u0 /= np.ones(
			(c, 1)).dot(np.atleast_2d(u0.sum(axis=0))).astype(np.float64)
		init = u0.copy()
	u0 = init
	u = np.fmax(u0, np.finfo(np.float64).eps)
	print("u.shape:", u.shape)

	# Initialize loop parameters
	jm = np.empty(0)
	p = 0

	# Main cmeans loop
	while p < maxiter - 1:
		u2 = u.copy()
		[cntr1, cntr2, u, Jjm, d1, d2, d] = _cmeans0(data1, data2, u2, c, w, m)
		jm = np.hstack((jm, Jjm))
		p += 1

		# Stopping rule
		if np.linalg.norm(u - u2) < error:
			break

	# Final calculations
	error = np.linalg.norm(u - u2)
	fpc = _fp_coeff(u)

	return cntr1, cntr2, u, u0, d1, d2, d, jm, p, fpc

def cmeans_predict(test_data, cntr_trained, m, error, maxiter, init=None,
				   seed=None):
	"""
	Prediction of new data in given a trained fuzzy c-means framework [1]_.

	Parameters
	----------
	test_data : 2d array, size (S, N)
		New, independent data set to be predicted based on trained c-means
		from ``cmeans``. N is the number of data sets; S is the number of
		features within each sample vector.
	cntr_trained : 2d array, size (S, c)
		Location of trained centers from prior training c-means.
	m : float
		Array exponentiation applied to the membership function u_old at each
		iteration, where U_new = u_old ** m.
	error : float
		Stopping criterion; stop early if the norm of (u[p] - u[p-1]) < error.
	maxiter : int
		Maximum number of iterations allowed.
	init : 2d array, size (S, N)
		Initial fuzzy c-partitioned matrix. If none provided, algorithm is
		randomly initialized.
	seed : int
		If provided, sets random seed of init. No effect if init is
		provided. Mainly for debug/testing purposes.

	Returns
	-------
	u : 2d array, (S, N)
		Final fuzzy c-partitioned matrix.
	u0 : 2d array, (S, N)
		Initial guess at fuzzy c-partitioned matrix (either provided init or
		random guess used if init was not provided).
	d : 2d array, (S, N)
		Final Euclidian distance matrix.
	jm : 1d array, length P
		Objective function history.
	p : int
		Number of iterations run.
	fpc : float
		Final fuzzy partition coefficient.

	Notes
	-----
	Ross et al. [1]_ did not include a prediction algorithm to go along with
	fuzzy c-means. This prediction algorithm works by repeating the clustering
	with fixed centers, then efficiently finds the fuzzy membership at all
	points.

	References
	----------
	.. [1] Ross, Timothy J. Fuzzy Logic With Engineering Applications, 3rd ed.
		   Wiley. 2010. ISBN 978-0-470-74376-8 pp 352-353, eq 10.28 - 10.35.

	"""
	c = cntr_trained.shape[0]

	# Setup u0
	if init is None:
		if seed is not None:
			np.random.seed(seed=seed)
		n = test_data.shape[1]
		u0 = np.random.rand(c, n)
		u0 /= np.ones(
			(c, 1)).dot(np.atleast_2d(u0.sum(axis=0))).astype(np.float64)
		init = u0.copy()
	u0 = init
	u = np.fmax(u0, np.finfo(np.float64).eps)

	# Initialize loop parameters
	jm = np.empty(0)
	p = 0

	# Main cmeans loop
	while p < maxiter - 1:
		u2 = u.copy()
		[u, Jjm, d] = _cmeans_predict0(test_data, cntr_trained, u2, c, m)
		jm = np.hstack((jm, Jjm))
		p += 1

		# Stopping rule
		if np.linalg.norm(u - u2) < error:
			break

	# Final calculations
	error = np.linalg.norm(u - u2)
	fpc = _fp_coeff(u)

	return u, u0, d, jm, p, fpc


def _cmeans_predict0(test_data, cntr, u_old, c, m):
	"""
	Single step in fuzzy c-means prediction algorithm. Clustering algorithm
	modified from Ross, Fuzzy Logic w/Engineering Applications (2010)
	p.352-353, equations 10.28 - 10.35, but this method to generate fuzzy
	predictions was independently derived by Josh Warner.

	Parameters inherited from cmeans()

	Very similar to initial clustering, except `cntr` is not updated, thus
	the new test data are forced into known (trained) clusters.

	"""
	# Normalizing, then eliminating any potential zero values.
	u_old /= np.ones((c, 1)).dot(np.atleast_2d(u_old.sum(axis=0)))
	u_old = np.fmax(u_old, np.finfo(np.float64).eps)

	um = u_old ** m
	test_data = test_data.T

	# For prediction, we do not recalculate cluster centers. The test_data is
	# forced to conform to the prior clustering.

	d = _distance(test_data, cntr)
	d = np.fmax(d, np.finfo(np.float64).eps)

	jm = (um * d ** 2).sum()

	u = d ** (- 2. / (m - 1))
	u /= np.ones((c, 1)).dot(np.atleast_2d(u.sum(axis=0)))

	return u, jm, d
