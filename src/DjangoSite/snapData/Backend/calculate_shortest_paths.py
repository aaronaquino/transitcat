#!/bin/env python2
"""Calculates the shortest paths between pairs of nodes in the network using multithreading."""
import cPickle as pickle
import travel_times
import os
from utils import clean_data_frame


NUM_THREADS = 4
NUM_SECONDS_PER_MINUTE = 60
TRANSFER_TIME = 3 * NUM_SECONDS_PER_MINUTE # Time needed to switch lines or between different types of transit.


def consecutive_times_init(l, n_d, i_n_e, d_p):
	global lock
	lock = l
	global node_dict
	node_dict = n_d
	global inter_network_edges
	inter_network_edges = i_n_e
	global directory_path
	directory_path = d_p


def travel_times_worker(network_name):
	''' Computes the time (in seconds) between each pair of consecutive stations on a line. Assumes
	that travel times between two stations are equal in both directions.

		Args:
			network_name (string): The network (madrid_metro, caltrain, etc.) being analyzed.

		Returns:
			A dict mapping pairs of node IDs to the travel time (in seconds) between those two
			stations. For two stations a and b, both (a, b) and (b, a) will be in the dict.

	'''
	lock.acquire()
	print 'Computing times between consecutive stops for: %s' % network_name
	lock.release()
	result = {}
	stop_times_df = clean_data_frame(directory_path + '/' + network_name.replace(" ", ""), txt_file='stop_times.txt', sortby=None)

	prev_stop_sequence = None
	prev_node_id = None
	prev_stop_time = None

	for cid, e in stop_times_df.iterrows():
		curr_stop_sequence = e['stop_sequence']
		curr_node_id = node_dict[str(e['stop_id'])]
		curr_stop_time = e['arrival_time']

		if prev_stop_sequence is not None and int(curr_stop_sequence) == prev_stop_sequence + 1 and ((prev_node_id, curr_node_id) not in result):
			time_delta = travel_times.calculate_gtfs_time_difference(prev_stop_time, curr_stop_time)
			if time_delta < 0:
				lock.acquire()
				print 'Time between stops was %d for stops: %s and %s' % (time_delta, prev_node_id, curr_node_id)
				lock.release()
			result[(prev_node_id, curr_node_id)] = time_delta
			result[(curr_node_id, prev_node_id)] = time_delta

		prev_stop_sequence = curr_stop_sequence
		prev_node_id = curr_node_id
		prev_stop_time = curr_stop_time

	# Add a constant transfer time for all edges between different networks
	if inter_network_edges is not None:
		for a, b in inter_network_edges:
			result[(a, b)] = TRANSFER_TIME
			result[(b, a)] = TRANSFER_TIME

	return result


def compute_consecutive_stop_times(G, networks, node_dict, inter_network_edges, data_location, save_location=None):
	''' Calculates the travel time in seconds between every pair of conesecutive stops in the network.

		Args:
			G (TNEANet): A TNEANet representing a PTN.
			networks (list): The networks (madrid_metro, caltrain, etc.) to be analyzed.
			node_dict (dict): A dict mapping stop_id to the corresponding node ID in the network.
			internetwork_edges (list): A list of tuples, where each tuple consists of a source node ID
                and a destination node ID.
			data_location (string): File path to the directory containing the networks being analyzed.
			save_location (string): File path to the directory where results should be saved.

		Returns:
			A dictionary, where a key is of the form (src_node_id, dst_node_id) and a value is the travel
			time between those stops in seconds.

	'''
	try:
		from multiprocessing import Pool as ThreadPool
		from multiprocessing import Lock
		from functools import partial
	except ImportError:
		print('Cannot execute multithreading.')
		exit()

	l = Lock()
	pool = ThreadPool(processes=NUM_THREADS, initializer=consecutive_times_init, initargs=(l,node_dict,inter_network_edges,data_location,))
	pairwise_travel_times = pool.map(travel_times_worker, networks)
	pool.close()
	pool.join()

	consecutive_station_times = {}
	for travel_times_dict in pairwise_travel_times:
		for edge in travel_times_dict.keys():
			consecutive_station_times[edge] = travel_times_dict[edge]

	if save_location is not None:
		with open(save_location + '/' + 'consecutive_station_times.pkl', 'wb+') as output:
			pickle.dump(consecutive_station_times, output, pickle.HIGHEST_PROTOCOL)

	return consecutive_station_times


def init(l, g, c_s_t, s_l):
	global lock
	lock = l
	global G
	G = g
	global consecutive_station_times
	consecutive_station_times = c_s_t
	global save_location
	save_location = s_l


def dijkstras_worker(src):
	''' Runs Dijkstra's on the given source node. Saves the results ../Data/Travel_Times as files
	of the form <node_id>.pkl. Each .pkl file contains two pickled objects: the shortest distances
	to every other node from node_id and the previous pointers for each of the shortest paths.

		Args:
			src (int): Node ID of the source node.

		Returns:
			(src, stop_name, stop_id, network_name, avg_path_length)

	'''
	stop_name = G.GetStrAttrDatN(src, 'stop_name')
	stop_id = G.GetStrAttrDatN(src, 'stop_id')
	network_name = G.GetStrAttrDatN(src, 'network_name')
	lock.acquire()
	print 'Running Dijkstra\'s on node %d (%s %s (%s))' % (src, stop_id, stop_name, network_name)
	lock.release()
	dist, prev, avg_path_length = travel_times.dijkstras(G, src, consecutive_station_times)

	stop_name = stop_name.replace('/', '-')

	if save_location is not None:
		print save_location + '/Travel_Times/' + str(src) + '_' + str(stop_name) + '_' + str(network_name) + '.pkl'

		with open(save_location + '/Travel_Times/' + str(stop_id) + '.pkl', 'wb+') as output:
			pickle.dump(dist, output, pickle.HIGHEST_PROTOCOL)
			pickle.dump(prev, output, pickle.HIGHEST_PROTOCOL)
			pickle.dump(avg_path_length, output, pickle.HIGHEST_PROTOCOL)

	e = (src, G.GetStrAttrDatN(src, 'stop_name'), G.GetStrAttrDatN(src, 'stop_id'), G.GetStrAttrDatN(src, 'network_name'), avg_path_length)

	return e
