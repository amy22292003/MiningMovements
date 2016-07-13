#!/usr/bin/env python3
"""
    command: 
    output map file to: 
"""
import datetime
import numpy
import os
import sys

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))
sys.path.append(PACKAGE_PARENT)

import Liu.custommodule.locationcluster as ccluster
import Liu.custommodule.cpygmaps as cpygmaps
import Liu.custommodule.fuzzycmeans as cfuzzy
import Liu.custommodule.location as clocation
import Liu.custommodule.trajectory as ctrajectory
import Liu.custommodule.user as cuser

"""parameters"""
FILTER_TIME_S = 1446350400 #2015/11/01 @ UTC-4
FILTER_TIME_E = 1451620800 #2016/01/01 @ UTC-4
CLUSTER_NUM = 30
ERROR = 0.000001
MAX_KTH = 30

"""file path"""
USER_POSTS_FILE = "./data/TravelerPosts"
OUTPUT_MAP = "./data/Result/LocationMap_" + str(CLUSTER_NUM) +\
    "k" + str(MAX_KTH) + "e" + str(ERROR) + ".html"
OUTPUT_CLUSTER = "./data/Result/LocationCluster_" + str(CLUSTER_NUM) +\
    "k" + str(MAX_KTH) + "e" + str(ERROR) + ".txt"

def set_location_user_count(locations):
    for key in locations.keys():
        users = set(a_post.uid for a_post in locations[key].posts)
        setattr(locations[key], "usercount", len(users))

def main(*argv):
    print("--------------------------------------")
    print("STARTTIME:", (datetime.datetime.now()))
    print("--------------------------------------")

    # set UNIXTIME
    global FILTER_TIME_S
    global FILTER_TIME_E
    if len(argv) > 0:
        FILTER_TIME_S = argv[0]
        FILTER_TIME_E = argv[1]
    
    # getting data
    locations = clocation.open_locations()
    users = cuser.open_users_posts_afile(USER_POSTS_FILE)

    print("Sampling users posts...")
    removes = []
    for key, a_user in users.items():
        posts = [x for x in a_user.posts if (x.time > FILTER_TIME_S) and (x.time < FILTER_TIME_E)]
        users[key].posts = posts
        if len(posts) == 0:
            removes.append(key)

    sequences = ctrajectory.split_trajectory_byday([a_user.posts for a_user in users.values() if len(a_user.posts) != 0])
    sequences = ctrajectory.remove_adjacent_location(sequences)
    sequences = ctrajectory.remove_short(sequences)
    removes = list(set(removes) | (set(users.keys()) - set([x[0].uid for x in sequences])))

    for key in removes:
        del users[key]
    print("  remain users #:", len(users.keys()))

    locations = clocation.fit_users_to_location(locations, users, "uid")
    set_location_user_count(locations)

    coordinate = numpy.array([(float(x.lat), float(x.lng)) for x in locations.values()])
    location_frequency = numpy.array([x.usercount for x in locations.values()])
    
    # intersect clustering with the kth locations in each cluster & location frequency as weight
    #cntr, u, u0, d, jm, p, fpc, cluster_membership = cfuzzy.cmeans_coordinate(coordinate.T, CLUSTER_NUM, MAX_KTH, location_frequency, e=ERROR, algorithm="kthCluster_LocationFrequency")
    cntr, u, u0, d, jm, p, fpc, cluster_membership = cfuzzy.cmeans_coordinate(coordinate.T, CLUSTER_NUM, MAX_KTH, location_frequency, e=ERROR, algorithm="Original")
    locations = ccluster.fit_locations_membership(locations, u, locations.keys())
    locations = ccluster.fit_locations_cluster(locations, cluster_membership, locations.keys())

    
    cpygmaps.output_clusters(\
        [(float(x.lat), float(x.lng), str(x.cluster) + " >> " + x.lname + " >>u:" + str(u[x.cluster, i])) for i, x in enumerate(locations.values())], \
        cluster_membership, CLUSTER_NUM, OUTPUT_MAP)

    #ccluster.output_location_cluster(locations.values(), "cluster", OUTPUT_CLUSTER)
    

    print("--------------------------------------")
    print("ENDTIME:", (datetime.datetime.now()))
    print("--------------------------------------")

    return users, locations

if __name__ == '__main__':
    main(*sys.argv[1:])
