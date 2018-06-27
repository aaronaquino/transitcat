#!/bin/env python2
'''Functions for helping test our static (i.e., non-Transitland) isochrone algorithms.'''
import snap
import isochrone_utils as iu
import pprint as pp
from datetime import datetime, date, time, timedelta

def create_test_network():
	G = snap.TNEANet.New()
	G.AddNode(0)
	G.AddNode(1)
	G.AddNode(2)
	G.AddNode(3)
	G.AddNode(4)

	#G.AddEdge(from, to, edge_id)
	G.AddEdge(0, 1, 0)
	G.AddEdge(1, 0, 1)
	G.AddEdge(0, 2, 2)
	G.AddEdge(2, 0, 3)
	G.AddEdge(2, 3, 4)
	G.AddEdge(3, 2, 5)
	G.AddEdge(3, 4, 6)
	G.AddEdge(4, 3, 7)
	G.AddEdge(4, 2, 8)
	G.AddEdge(2, 4, 9)
	G.AddEdge(1, 3, 10)
	G.AddEdge(3, 1, 11)

	G.AddStrAttrDatN(0, 'pa', 'stop_id')
	G.AddStrAttrDatN(1, 'mp', 'stop_id')
	G.AddStrAttrDatN(2, 'ca', 'stop_id')
	G.AddStrAttrDatN(3, 'm1', 'stop_id')
	G.AddStrAttrDatN(4, 'm2', 'stop_id')

	G.AddStrAttrDatN(0, 'Palo Alto', 'stop_name')
	G.AddStrAttrDatN(1, 'Menlo Park', 'stop_name')
	G.AddStrAttrDatN(2, 'California Ave', 'stop_name')
	G.AddStrAttrDatN(3, 'Mystery 1', 'stop_name')
	G.AddStrAttrDatN(4, 'Mystery 2', 'stop_name')

	G.AddFltAttrDatN(0, 37.443475, 'stop_lat')
	G.AddFltAttrDatN(1, 37.454856, 'stop_lat')
	G.AddFltAttrDatN(2, 37.429365, 'stop_lat')
	G.AddFltAttrDatN(3, 38, 'stop_lat')
	G.AddFltAttrDatN(4, 38, 'stop_lat')

	G.AddFltAttrDatN(0, -122.164614, 'stop_lon')
	G.AddFltAttrDatN(1, -122.182297, 'stop_lon')
	G.AddFltAttrDatN(2, -122.141927, 'stop_lon')
	G.AddFltAttrDatN(3, -122.141927, 'stop_lon')
	G.AddFltAttrDatN(4, -122.141927, 'stop_lon')

	node_dict = {'pa': 0, 'mp': 1, 'ca': 2, 'm1': 3, 'm2': 4}

	return G, node_dict


def create_test_edge_weights():
	weights = {(0, 1): 60, (1, 0): 60,
			   (0, 2): 120, (2, 0): 120,
			   (2, 3): 200, (3, 2): 200,
			   (3, 4): 100, (4, 3): 100,
			   (2, 4): 15, (4, 2): 15,
			   (1, 3): 15, (3, 1): 15}
	return weights


def create_test_starting_location():
	# Close to the Palo Alto Caltrain.
	return (37.442605, -122.165369)

def print_stuff(reachable_walking, reachable_final):
	print("The following are the stops reachable while walking: ")
	pp.pprint(reachable_walking)
	print("The following are the node_id's and the time_remaining: ")
	pp.pprint(reachable_final)


G, node_dict = create_test_network()
d = date(2018, 6, 3)
t = time(12, 30)
start_time = datetime.combine(d, t)
#reachable_stops_walking(start_coord, start_time, timespan, G, walking_speed=6):
reachable_walking = iu.reachable_stops_walking(create_test_starting_location(), start_time, timedelta(minutes=30), G)

reachable_walking = [{'start_time': start_time,
					  'stop_id': 'pa',
					  'stop_name': 'Palo Alto',
					  'time_elapsed': timedelta(seconds=0),
					  'time_remaining': timedelta(minutes=30)}]
#isochrone_stats(G, node_dict, start_stations, travel_times)
reachable_final = iu.isochrone_stats(G, node_dict, reachable_walking, create_test_edge_weights())

print_stuff(reachable_walking, reachable_final)