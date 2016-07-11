import datetime
import itertools
import lda
import numpy as np
import random
import skfuzzy
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import TfidfTransformer  
from sklearn.feature_extraction.text import CountVectorizer
import custommodule.customskfuzzy as cskfuzzy
import custommodule.location as clocation

"""parameters"""
RAND_SEED_K = 0
RAND_SEED_INIT = 10
CLUSTER_DIST_THRESHOLD = 0.9

def get_tag_vector(corpus):
    print("[fuzzy c means] getting tag vector...")
    vectorizer = CountVectorizer()
    vector = vectorizer.fit_transform(corpus) # location # x tags #
    feature_name =vectorizer.get_feature_names() # tags #
    print("-- vector shape:", vector.shape)
    return vector.toarray(), feature_name

def get_tfidf(corpus):
    transformer = TfidfTransformer()
    vector, feature_name = get_tag_vector(corpus)
    print("vector:", vector.shape)
    tfidf = transformer.fit_transform(vector)
    return tfidf.toarray(), feature_name

"""LDA"""
def fit_lda(corpus, tag_name, topic_num):
    print("[fuzzy c means] LDA")
    model = lda.LDA(n_topics = topic_num, n_iter = 1000)
    model.fit(corpus)
    topic_word = model.topic_word_
    doc_topic = model.doc_topic_
    print("--loglikelihood:", model.loglikelihood())
    print("--")
    for i, topic_dist in enumerate(topic_word):
        topic_words = np.array(tag_name)[np.argsort(topic_dist)][:-(10+1):-1] # show the top 10 words in each topic
        print('  Topic {}: {}'.format(i, ' '.join(topic_words)))
    return topic_word, doc_topic

"""Location Clustering"""
def cmeans_ori(array, cluster_num):
    cntr, u, u0, d, jm, p, fpc = skfuzzy.cluster.cmeans(array, cluster_num, 2, error=0.01, maxiter=100, init=None)
    cluster_membership = np.argmax(u, axis=0)
    return cntr, u, u0, d, jm, p, fpc, cluster_membership

# w = the weight of gps side
def cmeans_comb(coordinate, tag_feature, cluster_num, w = 0.4, e = 0.01):
    print("[fuzzy c means] - gps + relation")
    cntr1, cntr2, u, u0, d1, d2, d, jm, p, fpc = cskfuzzy.cluster.cmeans(coordinate, tag_feature, cluster_num, w, 2, error=e, maxiter=100)
    cluster_membership = np.argmax(u, axis=0)
    return cntr1, cntr2, u, u0, d1, d2, d, jm, p, fpc, cluster_membership

def cmeans_intersect(coordinate, similarity, cluster_num, *para, w = 0.4, e = 0.01, algorithm="Original"):
    print("[fuzzy c means] - gps + relation")
    cntr1, u, u0, d1, d2, d, jm, p, fpc = cskfuzzy.cluster.cmeans_intersect(coordinate, similarity, cluster_num, w, 2, e, 100, algorithm, *para)
    cluster_membership = np.argmax(u, axis=0)
    return cntr1, u, u0, d1, d2, d, jm, p, fpc, cluster_membership

def cmeans_coordinate(coordinate, cluster_num, *para, e = 0.01, algorithm="Original"):
    print("[fuzzy c means] - gps")
    cntr, u, u0, d, jm, p, fpc = cskfuzzy.cluster.cmeans_coordinate(coordinate, cluster_num, 2, e, 100, algorithm, *para)
    cluster_membership = np.argmax(u, axis=0)
    return cntr, u, u0, d, jm, p, fpc, cluster_membership

"""Sequence Clustering"""
def _get_init_u(level, cluster_num, sequences1, sequences2, k, w):
    distance = np.ones((cluster_num, len(sequences1)))

    np.random.seed(RAND_SEED_INIT)
    init = np.random.randint(0, len(sequences1) - 1, 1)
    distance[0,:] = cskfuzzy.cluster.get_distance(level, w, sequences1, sequences2, np.array(sequences1)[init], np.array(sequences2)[init])   
    
    random.seed(RAND_SEED_INIT)
    # get far away cluster initial
    for c in range(1, cluster_num):
        far_cluster = list(np.where((distance[0:c, :] >= CLUSTER_DIST_THRESHOLD).all(axis=0))[0])
        if len(far_cluster) == 0:
            far_cluster = [np.argmax(distance[0:c, :].sum(axis=0))]
        add_init = random.sample(far_cluster, 1)
        distance[c,:] = cskfuzzy.cluster.get_distance(level, w, sequences1, sequences2, np.array(sequences1)[add_init], np.array(sequences2)[add_init])   
        init = np.append(init, add_init)
    print("[fuzzy c means]- get_init_u> \n-- init:", init)

    # get enough k sequences for each cluster
    #u = np.zeros((cluster_num, len(sequences1)))
    filter_k = lambda row:row <= sorted(row)[k - 1]
    large_k_indices = np.apply_along_axis(filter_k, axis=1, arr=distance)
    u = large_k_indices.astype(int)

    random.seed(RAND_SEED_K)
    print("--each cluster initial # before random choose:", u.sum(axis=1))
    for i in range(cluster_num):
        if sum(u[i, :]) > k:
            indices = [i for i, x in enumerate(u[i, :]) if x == 1]
            rand_k = random.sample(indices, k)
            u[i, :] = 0
            u[i, :][rand_k] = 1
    print("--each cluster initial #:", u.sum(axis=1))
    return u

"""
def sequences_clustering(level, sequences, cluster_num, *para, e = 0.001, algorithm = "Original"):
    print("[fuzzy c means] Sequence Clustering - level:", level)
    print("--data:")
    distance = cskfuzzy.cluster.get_distance(level, sequences)
    k = para[0]
    if algorithm is "Original":
        # get init
        u = _get_init_u(level, cluster_num, k, distance.shape[0], distance = distance)
        du, u0, d, jm, p, fpc = cskfuzzy.cluster.cmeans_nocenter(distance, cluster_num, 2, e, 100, algorithm, k, init = u)
    else:
        # get distance of semantic sequences
        print("--data 2:")
        distance2 = cskfuzzy.cluster.get_distance(level, para[1])
        if algorithm is "2Distance":
            # get init
            u = _get_init_u(level, cluster_num, k, distance.shape[0], distance = distance * distance2)
            u, u0, d, jm, p, fpc = cskfuzzy.cluster.cmeans_nocenter(distance, cluster_num, 2, e, 100, algorithm, k, distance2, init = u) 
        else:
            w = para[2]
            # get init
            u = _get_init_u(level, cluster_num, k, distance.shape[0], distance = w * distance + (1-w) * distance2)
            u, u0, d, jm, p, fpc = cskfuzzy.cluster.cmeans_nocenter(distance, cluster_num, 2, e, 100, algorithm, k, distance2, para[2], init = u)
    
    print("-- looping time:", p)
    cluster_membership = np.argmax(u, axis=0)
    return u, u0, d, jm, p, fpc, cluster_membership, distance
"""

def sequences_clustering_i(level, sequences, cluster_num, *para, e = 0.001, algorithm = "2WeightedDistance"):
    print("[fuzzy c means] Sequence Clustering - level:", level)
    k = para[0]
    sequences2 = para[1]
    w = para[2]

    u = _get_init_u(level, cluster_num, sequences, sequences2, k, w)
    u, u0, d, jm, p, fpc, center = cskfuzzy.cluster.cmeans_nocenter_i(sequences, cluster_num, 2, e, 30, algorithm, level, k, sequences2, w, init = u)

    print("-- looping time:", p)
    cluster_membership = np.argmax(u, axis=0)
    return u, u0, d, jm, p, fpc, center, cluster_membership