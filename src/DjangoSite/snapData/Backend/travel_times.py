#!/bin/env python2
"""Functions for calculating the shortest paths between pairs of nodes in the network."""
import cPickle as pickle
from fib_heap import Fibonacci_heap
import numpy as np
import snap
import sys
import pandas as pd



NUM_SECONDS_PER_MINUTE = 60
TRANSFER_TIME = 3 * NUM_SECONDS_PER_MINUTE # Time needed to switch lines or between different types of transit.


def calculate_gtfs_time_difference(start_time, end_time):
	''' Computes the time (in seconds) between two GTFS time strings, which are in the form (H)H:MM:SS.
	For example, if a trip begins at 10:30:00 p.m. and ends at 2:15:00 a.m. on the following day,
	the stop times would be 22:30:00 and 26:15:00.

		Args:
			start_time (string)
			end_time (string)

		Returns:
			Integer representing the elapsed time (in seconds). 

	'''
	start_time_components = start_time.split(':')
	end_time_components = end_time.split(':')
	for i in range(len(start_time_components)):
		start_time_components[i] = int(start_time_components[i])
	for i in range(len(end_time_components)):
		end_time_components[i] = int(end_time_components[i])

	result = 0

	# Compute difference in seconds.
	if end_time_components[2] < start_time_components[2]:
		end_time_components[2] += NUM_SECONDS_PER_MINUTE
		end_time_components[1] -= 1
	result += end_time_components[2] - start_time_components[2]

	# Repeat for minutes.
	if end_time_components[1] < start_time_components[1]:
		end_time_components[1] += NUM_SECONDS_PER_MINUTE
		end_time_components[0] -= 1
	result += ((end_time_components[1] - start_time_components[1]) * NUM_SECONDS_PER_MINUTE)

	# Repeat for hours.
	result += ((end_time_components[0] - start_time_components[0]) * NUM_SECONDS_PER_MINUTE * NUM_SECONDS_PER_MINUTE)

	return result



def calculate_times_between_successive_stations(networks, node_dict, inter_network_edges=None):
	''' Computes the time (in seconds) between each pair of consecutive stations on a line. Assumes
	that travel times between two stations are equal in both directions.

		Args:
			networks (list): The networks (Metro, Autobuses_Urbanos, etc.) being analyzed.
			node_dict (dict): A dict mapping stop_id to node ID in the SNAP graph.
			inter_network_edges (list): A list of edges of the form (node_id, node_id) representing
				edges between two different transit networks. These edges will be added to the
				result dict with a constant time to symolize transferring.

		Returns:
			A dict mapping pairs of node IDs to the travel time (in seconds) between those two
			stations. For two stations a and b, both (a, b) and (b, a) will be in the dict.

	'''
	travel_times = {}
	for network_name in networks:
		print network_name
		stop_times_df = pd.read_csv(network_name + '/stop_times.txt')

		prev_stop_sequence = None
		prev_node_id = None
		prev_stop_time = None

		for cid, e in stop_times_df.iterrows():
			curr_stop_sequence = e['stop_sequence']
			curr_node_id = node_dict[e['stop_id']]
			curr_stop_time = e['arrival_time']

			if prev_stop_sequence is not None and int(curr_stop_sequence) == prev_stop_sequence + 1 and ((prev_node_id, curr_node_id) not in travel_times):
				time_delta = calculate_gtfs_time_difference(prev_stop_time, curr_stop_time)
				if time_delta < 0:
					print 'Time between stops was %d for stops: %s and %s' % (time_delta, prev_node_id, curr_node_id)
				travel_times[(prev_node_id, curr_node_id)] = time_delta
				travel_times[(curr_node_id, prev_node_id)] = time_delta

			prev_stop_sequence = curr_stop_sequence
			prev_node_id = curr_node_id
			prev_stop_time = curr_stop_time

	# Add a constant transfer time for all edges between different networks
	if inter_network_edges is not None:
		for a, b in inter_network_edges:
			travel_times[(a, b)] = TRANSFER_TIME
			travel_times[(b, a)] = TRANSFER_TIME

	return travel_times


def dijkstras(G, src, consecutive_station_times):
	''' Computes the shortest path from the source node to any other node in the network.
		Uses the pseudocode for Dijkstra's algorithm using a Fibonacci heap described here:
		https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm#Using_a_priority_queue.

		Args:
			G (TNEANet)
			src (int): Node ID of the source node.
			consecutive_station_times (dict): A dict mapping pairs of node IDs of successive
				stations to the travel time (in seconds) between those two stations.

		Returns:
			distances (dict): A dict mapping destination node IDs to the shortest time (in seconds)
				needed to get there from src.
			previous (dict): A dict mapping a node ID dest to the previous node ID of the shortest
				path from src to dest.
			avg_path_length (float): The average time (in seconds) of all the shortest paths from src
				to all other nodes.

	'''
	distances = {}
	previous = {}
	# The most recent route_id used to get to a node so far.
	routes = {}
	# Set the distance for the start node to zero.
	distances[src] = 0

	Q = Fibonacci_heap()
	node_id_to_heap_node_dict = {}
	for NI in G.Nodes():
		node_id = NI.GetId()
		routes[node_id] = None
		if node_id != src:
			distances[node_id] = sys.maxint
			previous[node_id] = None
			node = Q.enqueue(node_id, sys.maxint)
			node_id_to_heap_node_dict[node_id] = node
		else:
			node = Q.enqueue(src, 0)
			node_id_to_heap_node_dict[src] = node

	while Q.m_min is not None:
		u = Q.dequeue_min()
		current = u.get_value()
		NI = G.GetNI(current)
		for neighbor in NI.GetOutEdges():
			if (current, neighbor) not in consecutive_station_times:
				alt = distances[current] + TRANSFER_TIME
			else:
				alt = distances[current] + consecutive_station_times[(current, neighbor)]

			# Penalize transfers.
			if routes[current] is not None:
				neighbor_routes = G.GetStrAttrDatN(neighbor, 'routes').split(',')
				if routes[current] not in neighbor_routes:
					alt += TRANSFER_TIME

			if alt < distances[neighbor]:
				distances[neighbor] = alt
				previous[neighbor] = current

				current_routes = set(G.GetStrAttrDatN(current, 'routes').split(','))
				neighbor_routes = set(G.GetStrAttrDatN(neighbor, 'routes').split(','))
				common_route = current_routes & neighbor_routes
				if len(common_route) == 0:
					# Moving from one type of transit to the other.
					routes[neighbor] = None
				else:
					routes[neighbor] = list(common_route)[0]

				neighbor_node = node_id_to_heap_node_dict[neighbor]
				Q.decrease_key(neighbor_node, alt)

	# Compute the average path length. First eliminate any distances still equal to sys.maxint
	# (indicating a path was not found).
	for nid in distances.keys():
		if distances[nid] == sys.maxint:
			del distances[nid]
	times = [t for t in distances.values()]

	# Disregard the source to source path, which has length 0.
	if 0 in times:
		times.remove(0)
	avg_path_length = np.mean(times)

	return distances, previous, avg_path_length


def compute_all_shortest_paths(G, consecutive_station_times):
	''' Computes the time (in seconds) needed to travel between any two nodes in the network.
	Saves the results ../Data/Travel_Times as files of the form <node_id>.pkl. Each .pkl file
	contains two pickled objects: the shortest distances to every other node from node_id and
	the previous pointers for each of the shortest paths.

		Args:
			G (TNEANet)
			consecutive_station_times (dict): A dict mapping pairs of node IDs of successive
				stations to the travel time (in seconds) between those two stations.

		Returns:
			None

	'''
	node_average_paths = []
	entry_with_longest_time = (None, None, -1)
	num_most_central_nodes = 10

	for NI in G.Nodes():
		src = NI.GetId()
		print 'Running Dijkstra\'s on node %d (%s)' % (src, G.GetStrAttrDatN(src, 'stop_name'))
		dist, prev, avg_path_length = dijkstras(G, src, consecutive_station_times)

		# Keep track of most central nodes (i.e., nodes with the lowest average travel times).
		if len(node_average_paths) < num_most_central_nodes:
			e = (G.GetStrAttrDatN(src, 'stop_name'), G.GetStrAttrDatN(src, 'network_abr'), avg_path_length)
			node_average_paths.append(e)
			if avg_path_length > entry_with_longest_time[2]:
				entry_with_longest_time = e
		else:
			if avg_path_length < entry_with_longest_time[2]:
				node_average_paths.remove(entry_with_longest_time)
				e = (G.GetStrAttrDatN(src, 'stop_name'), G.GetStrAttrDatN(src, 'network_abr'), avg_path_length)
				node_average_paths.append(e)
				entry_with_longest_time = max(node_average_paths, key = lambda t: t[2])

		with open('../../../../../Results/Travel_Times/' + str(src) + '.pkl', 'wb+') as output:
			pickle.dump(dist, output, pickle.HIGHEST_PROTOCOL)
			pickle.dump(prev, output, pickle.HIGHEST_PROTOCOL)


	for name, network, time in sorted(node_average_paths, key=lambda e: e[2]):
		print '%s (%s) has average time %f' % (name, network, time)



