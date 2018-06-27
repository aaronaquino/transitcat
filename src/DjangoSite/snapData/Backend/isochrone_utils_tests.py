#!/bin/env python2
# -*- coding: utf-8 -*-
"""Tests for isochrone utils functions."""
from isochrone_utils import is_valid_transitland_feed, add_onestop_ids_to_network, get_nearby_date_for_weekday, get_stations_reachable_from_source, compute_walking_time_between_points, reachable_stops_walking_transitland
from datetime import timedelta
from edges import create_l_space_graph, get_internetwork_edges
from nodes import create_node_network
from utils import save_graph, load_graph
import cPickle as pickle
import snap

DATA_LOCATION = '../../../../../Data'
RESULTS_LOCATION = '../../../../../Results'
networks = ['caltrain']


# # Test our ability to validate Transitland Feed Onestop IDs.

# print('Validating various Transitland feeds...')
# assert is_valid_transitland_feed('f-9q9-caltrain')
# assert is_valid_transitland_feed('f-9q9-bart')
# assert is_valid_transitland_feed('f-ezjm-informaciónoficial~consorcioregionaldetransportesdemadrid')


# # Test our ability to query schedule information.

# # Get nearby date for Wednesday at 3:30:45pm.
# print(get_nearby_date_for_weekday(2, 15, 30, 45))

# # Get nearby date for Monday at 9:15am.
# print(get_nearby_date_for_weekday(0, 9, 15))

# # Query for trains leaving the Palo Alto Caltrain within 30 minutes of 5:00pm on a Wednesday.
# source_id = 's-9q9jh061xw-paloaltocaltrain<70171'
# start_time = get_nearby_date_for_weekday(2, 17, 00, 00)
# end_time = start_time + timedelta(minutes=30)
# print(get_stations_reachable_from_source(source_id, start_time, end_time))

# # Query for trains leaving the Embarcadero BART within 90 minutes of 11:30pm on a Wednesday.
# source_id = 's-9q8znb12j1-embarcadero'
# start_time = get_nearby_date_for_weekday(2, 23, 30, 00)
# end_time = start_time + timedelta(minutes=90)
# print(get_stations_reachable_from_source(source_id, start_time, end_time))


# # Test our ability to compute the time for walking between two points.

# # Walk from 1047 to ZAP.

# zap_coordinates = (37.421353, -122.161945)
# ten_forty_seven_coordinates = (37.419911, -122.170896)
# print(compute_walking_time_between_points(zap_coordinates[0], zap_coordinates[1], ten_forty_seven_coordinates[0], ten_forty_seven_coordinates[1]))


# # Test our ability to get stations walkable within a certain timeframe.

# # Query for Caltrain stations within 45 minutes walking from Thaiphoon on Tuesday evening starting at 8.30pm.

thaiphoon_coordinates = (37.444270, -122.161809)
start_time = get_nearby_date_for_weekday(1, 20, 30)
timespan = timedelta(minutes=45)
print(reachable_stops_walking_transitland('f-9q9-caltrain', thaiphoon_coordinates, start_time, timespan))

# # Query for Madrid metro stations within 15 minutes walking from Aaron's homestay on Monday morning starting at 9.00am.

aaron_homestay_coordinates = (40.418742, -3.707538)
start_time = get_nearby_date_for_weekday(0, 9, 0)
timespan = timedelta(minutes=5)
print(reachable_stops_walking_transitland('f-ezjm-informaciónoficial~consorcioregionaldetransportesdemadrid', aaron_homestay_coordinates, start_time, timespan))


# Test our ability to create a SNAP network from GTFS files and then update the network with
# Transitland Onestop ID information.

# # Create graph.

# G, node_dict = create_node_network(networks, DATA_LOCATION)
# G = create_l_space_graph(G, node_dict, networks, DATA_LOCATION)
# print 'Graph created with %d nodes and %d edges' % (G.GetNodes(), G.GetEdges())
# G, inter_network_edges = get_internetwork_edges(G, 100)
# print 'Updated graph now has %d nodes and %d edges' % (G.GetNodes(), G.GetEdges())

# try:
#     print('Saving graph...')
#     save_graph(G, RESULTS_LOCATION + '/' + 'caltrain.graph')
#     with open(RESULTS_LOCATION + '/' + 'caltrain.pkl', 'wb+') as output:
#         pickle.dump(node_dict, output, pickle.HIGHEST_PROTOCOL)
#         pickle.dump(inter_network_edges, output, pickle.HIGHEST_PROTOCOL)
#     print('Done!')
# except IOError:
#     print('Could not save node network!')


# # Load graph.

# node_dict = None
# inter_network_edges = None
# G = None

# try:
# 	# Load node_dict and related metadata.
# 	with open(RESULTS_LOCATION + '/' + 'caltrain.pkl', 'rb') as output:
# 		node_dict = pickle.load(output)
# 		inter_network_edges = pickle.load(output)

# 	# Load L-space graph.
# 	G = load_graph(RESULTS_LOCATION + '/' + 'caltrain.graph')
# except IOError:
# 	print("Could not load cached graph!")

# print 'Graph loaded with %d nodes and %d edges' % (G.GetNodes(), G.GetEdges())


# # Update the network with Transitland Onestop ID information.

# G = add_onestop_ids_to_network(G, {'caltrain': 'f-9q9-caltrain'})

