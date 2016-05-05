"""
Fuzzy clustering subpackage, containing fuzzy c-means clustering algorithm.
This can be either supervised or unsupervised, depending if U_init kwarg is
used (if guesses are provided, it is supervised).

"""
__all__ = ['cmeans',
           'cmeans_predict',
           'cmeans_intersect',
           'cmeans_coordinate',
           'cmeans_nocenter'
           ]

from ._cmeans import cmeans, cmeans_predict

from ._cmeans_intersect import cmeans as cmeans_intersect

from ._cmeans_coordinate import cmeans as cmeans_coordinate

from ._cmeans_nocenter import cmeans as cmeans_nocenter

from .distance import *