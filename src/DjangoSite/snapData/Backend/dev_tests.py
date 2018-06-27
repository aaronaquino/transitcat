#!/bin/env python2
'''Utility functions for cleaning data frames and related objects.'''
from utils import save_graph, load_graph
import calculate_shortest_paths as csp
from nodes import create_node_network
import snap
import isochrone_utils as iu
import pprint as pp
from datetime import datetime, date, time, timedelta
import cPickle as pickle

'''
Put the name of the network you would like to test here
'''
network_name = "madrid"

DATA_LOCATION = '../../../../../Data/' + network_name
RESULTS_LOCATION = '../../../../../Data/' + network_name

node_dict = None
inter_network_edges = None
G = None

try:
	# Load node_dict and related metadata.
	with open(RESULTS_LOCATION + '/' + network_name + '.pkl', 'rb') as output:
		node_dict = pickle.load(output)
		inter_network_edges = pickle.load(output)

	# Load L-space graph.
	G = load_graph(RESULTS_LOCATION + '/' + network_name + '.graph')
except IOError:
	print("Could not load cached graph!")

print 'Graph loaded with %d nodes and %d edges' % (G.GetNodes(), G.GetEdges())
print 'Now loading travel times between edges'


try:
	with open(RESULTS_LOCATION + '/' + 'consecutive_station_times.pkl', 'rb') as output:
		travel_times = pickle.load(output)
except IOError:
	print("Could not load cached travel times!")

### GET EDGE WEIGHTS

PALO_ALTO = (37.442605, -122.165369)
MISSION_DISTRICT = (37.758290, -122.416239)
MADRID_CENTER = (40.410081, -3.706815)


d = date(2018, 6, 3)
t = time(12, 30)
start_time = datetime.combine(d, t)
#reachable_stops_walking(start_coord, start_time, timespan, G, walking_speed=6):
reachable_walking = iu.reachable_stops_walking(MADRID_CENTER,
											   start_time, timedelta(minutes=20), G)
#compute_consecutive_stop_times(G, networks, node_dict, inter_network_edges, data_location, save_location=None):
#travel_times = csp.compute_consecutive_stop_times(G, ['CT-GTFS'], node_dict, [], '../../../../../Data', '../../../../../Data/CT-PKL')
reachable_final = iu.isochrone_stats(G, node_dict, reachable_walking, travel_times)

print "Reachable nodes with remaining times: "
pp.pprint(reachable_final)


# pp.pprint(result)

# Function takes in a stop, arrival time
# 
