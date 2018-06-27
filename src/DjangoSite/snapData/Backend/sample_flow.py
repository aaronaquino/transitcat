#!/bin/env python2
"""Shows how a majority of the backend graph analysis functions can/should be used. The general flow is to
create a node network, add edges to form a L-space graph, calculate the times between consecutive stops, and
then run criticality computations."""
import cPickle as pickle
import numpy as np
import snap
import sys
from calculate_criticality import get_avg_farness_centrality, get_criticality, get_criticality_by_edge_id
from calculate_shortest_paths import consecutive_times_init, travel_times_worker, compute_consecutive_stop_times, init, dijkstras_worker
from edges import create_l_space_graph, get_internetwork_edges
from nodes import create_node_network
from utils import save_graph, load_graph


DATA_LOCATION = '../../../../../Data'
RESULTS_LOCATION = '../../../../../Results'
networks = ['madrid_metro', 'madrid_cercanias']


# # Create graph.

# G, node_dict = create_node_network(networks, DATA_LOCATION)
# G = create_l_space_graph(G, node_dict, networks, DATA_LOCATION)
# print 'Graph created with %d nodes and %d edges' % (G.GetNodes(), G.GetEdges())
# G, inter_network_edges = get_internetwork_edges(G, 100)
# print 'Updated graph now has %d nodes and %d edges' % (G.GetNodes(), G.GetEdges())

# try:
#     print('Saving graph...')
#     save_graph(G, RESULTS_LOCATION + '/' + 'madrid.graph')
#     with open(RESULTS_LOCATION + '/' + 'madrid.pkl', 'wb+') as output:
#         pickle.dump(node_dict, output, pickle.HIGHEST_PROTOCOL)
#         pickle.dump(inter_network_edges, output, pickle.HIGHEST_PROTOCOL)
#     print('Done!')
# except IOError:
#     print('Could not save node network!')


# Load graph.

node_dict = None
inter_network_edges = None
G = None

try:
	# Load node_dict and related metadata.
	with open(RESULTS_LOCATION + '/' + 'bay_area.pkl', 'rb') as output:
		node_dict = pickle.load(output)
		inter_network_edges = pickle.load(output)

	# Load L-space graph.
	G = load_graph(RESULTS_LOCATION + '/' + 'bay_area.graph')
except IOError:
	print("Could not load cached graph!")

print 'Graph loaded with %d nodes and %d edges' % (G.GetNodes(), G.GetEdges())


# Compute times between consecutive stops.

# consecutive_station_times = compute_consecutive_stop_times(G, networks, node_dict, inter_network_edges, DATA_LOCATION, RESULTS_LOCATION)

# print 'Writing results to consecutive_station_times.txt.'
# try:
# 	with open(RESULTS_LOCATION + '/' + 'consecutive_station_times.txt', 'wb+') as output:
# 		for edge, weight in consecutive_station_times.items():
# 			output.write('%d %d %d\n' % (edge[0], edge[1], weight))
# except IOError:
# 	print 'Could not create consecutive_station_times.txt.'


# Compute average farness centrality for the network.

consecutive_station_times_path = RESULTS_LOCATION + '/' + 'consecutive_station_times_bay_area.pkl'
avg_farness_centrality = get_avg_farness_centrality(G, consecutive_station_times_path)
print(avg_farness_centrality)


# Get criticality for a given edge.

# For the Bay Area (Caltrain + BART) network, node 26 is Millbrae (BART) and node 53 is Millbrae (Caltrain).
criticality = get_criticality(G, 26, 53, consecutive_station_times_path, avg_farness_centrality)
print(criticality)

# For the Madrid metro + cercanias network, node 3 is Sol (metro) and node 268 is Sol (cercanias).
# criticality = get_criticality(G, 3, 268, consecutive_station_times_path, avg_farness_centrality)

# We can also compute criticality by passing in the edge ID. The ID of the Sol edge above is 926.
# criticality = get_criticality_by_edge_id(G, 926, consecutive_station_times_path, avg_farness_centrality)

