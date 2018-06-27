#!/bin/env python2
"""Functions for computing criticality for a given edge."""
import cPickle as pickle
import numpy as np
import json
import os
import snap
import sys
from calculate_shortest_paths import init, dijkstras_worker, compute_consecutive_stop_times


NUM_THREADS = 4

def get_avg_farness_centrality(G, consecutive_station_times_path, save_location=None):
	''' Calculates the average farness centrality for the given network. Farness centrality for a
	node is the average shortest path length to all other nodes that reside in the same connected
	component as the given node.

	If save_location is provided, we also save individual .pkl files for each node containing
	relevant farness centrality information (e.g., the actual shortest paths). At the end we also
	save a summary of our findings to avg_path_length_summary.txt. 

		Args:
			G (TNEANet): A TNEANet representing a PTN.
			consecutive_station_times_path (string): File path to .pkl file containing conesecutive
				station times (see defintion in travel_times_worker() in calculate_shortest_paths.py).
			save_location (string): File path to the directory where results should be saved.

		Returns:
			The average farness centrality of the network.

	'''
	print 'Loading conesecutive_station_times.pkl.'
	consecutive_station_times = {}
	with open(consecutive_station_times_path, 'rb') as output:
		consecutive_station_times = pickle.load(output)

	try:
		from multiprocessing import Pool as ThreadPool
		from multiprocessing import Lock
		from functools import partial
	except ImportError:
		print('Cannot execute multithreading.')
		exit()

	print 'Creating a list of nodes to distribute among the threads.'
	node_ids = [node.GetId() for node in G.Nodes()]
	print 'Starting a thread pool with %d threads.' % NUM_THREADS
	sys.stdout.flush()

	l = Lock()
	pool = ThreadPool(processes=NUM_THREADS, initializer=init, initargs=(l,G,consecutive_station_times,save_location,))
	average_path_lengths = pool.map(dijkstras_worker, node_ids)
	pool.close()
	pool.join()

	farness_centralities = [x[4] for x in average_path_lengths]
	avg_farness_centrality = np.mean(farness_centralities)

	if save_location is not None:
		print 'Writing the results to avg_path_length_summary.txt.'
		sys.stdout.flush()
		path_lengths = [x[4] for x in average_path_lengths]
		try:
			with open(save_location + '/avg_path_length_summary.txt', 'wb+') as output:
				output.write('Average shortest path over the entire network: %f\n' % avg_farness_centrality)
				for node_id, stop_name, stop_id, network_abr, avg_shortest_path in average_path_lengths:
					output.write(str(stop_name) + ',' + str(node_id) + ',' + str(stop_id) + ',' + str(avg_shortest_path) + '\n')
		except IOError:
			print 'Could not create summary file.'
	print average_path_lengths

	return avg_farness_centrality



def get_criticality(G, src_node, dst_node, consecutive_station_times_path, avg_farness_centrality=-1.0):
	''' Calculates the criticality of a given edge in the network.

		Args:
			G (TNEANet): A TNEANet representing a PTN.
			src_node (int): Node ID of the source node.
			dst_node (int): Node ID of the destination node.
			consecutive_station_times_path (string): File path to .pkl file containing conesecutive
				station times (see defintion in travel_times_worker() in calculate_shortest_paths.py).
			avg_farness_centrality (float): The average farness centrality of the network. If this value
				is not provided then we calculate it ourselves.

		Returns:
			The criticality (float) of the given edge, which is the increase in the average farness centrality
			when that edge is removed from the network. If removing the edge splits the network into two
			components, return -1.0.

	'''
	if avg_farness_centrality == -1.0:
		avg_farness_centrality = get_avg_farness_centrality(G);
	print 'Original average farness centrality is %f' % avg_farness_centrality

	if not G.IsNode(src_node) or not G.IsNode(dst_node):
		raise RuntimeError('Error while computing criticality: invalid node IDs provided for edge to remove.')

	# Since edges are bidirectional for a TNEANet, we remove both from the network.
	G.DelEdge(src_node, dst_node)
	G.DelEdge(dst_node, src_node)

	updated_farness_centrality = get_avg_farness_centrality(G, consecutive_station_times_path, save_location=None)
	print 'Updated average farness centrality is %f' % updated_farness_centrality
	criticality = updated_farness_centrality - avg_farness_centrality

	# Criticality will be negative if the edge we removed split the network into two components.
	if criticality < 0:
		return -1.0

	return criticality


def get_criticality_by_edge_id(G, edge_id, consecutive_station_times_path, avg_farness_centrality=-1.0):
	''' Calculates the criticality of a given edge in the network.

		Args:
			G (TNEANet): A TNEANet representing a PTN.
			edge_id (int): Edge ID of the edge to be removed.
			consecutive_station_times_path (string): File path to .pkl file containing conesecutive
				station times (see defintion in travel_times_worker() in calculate_shortest_paths.py).
			avg_farness_centrality (float): The average farness centrality of the network. If this value
				is not provided then we calculate it ourselves.

		Returns:
			The criticality of the given edge, which is the increase in the average farness centrality
			when that edge is removed from the network.

	'''
	EI = G.GetEI(edge_id)
	src_node = EI.GetSrcNId()
	dst_node = EI.GetDstNId()

	return get_criticality(G, src_node, dst_node, consecutive_station_times_path, avg_farness_centrality)

def remap_keys(mapping):
	return [{'key':k, 'value': v} for k, v in mapping.iteritems()]

def create_average_farness_centrality_files(request, name, graph, networks, node_dict, internetwork_edges):
	if request.session.get('travel_times') == None:
		request.session['travel_times'] = {}
	DATA_LOCATION = "../../../Results"
	RESULTS_LOCATION = "../../../Results/" + name.replace(" ", "") + "-AdditionalData"
	if not os.path.exists(RESULTS_LOCATION):
		os.makedirs(RESULTS_LOCATION)

	consecutive_station_times_path = RESULTS_LOCATION + '/' + 'consecutive_station_times.pkl'
	if name not in request.session.get('travel_times'):

		if not os.path.exists(RESULTS_LOCATION + '/Travel_Times/'):
			os.makedirs(RESULTS_LOCATION + '/Travel_Times/')
		travel_times = compute_consecutive_stop_times(graph, networks, node_dict, internetwork_edges, DATA_LOCATION, RESULTS_LOCATION)
		request.session['travel_times'][name] = json.dumps(remap_keys(travel_times))
	travel_times = request.session.get('travel_times')[name]

	avg_farness_centrality = get_avg_farness_centrality(graph, consecutive_station_times_path, RESULTS_LOCATION)


	if request.session.get('avg_farness_centrality') == None:
		request.session['avg_farness_centrality'] = {}
	request.session['avg_farness_centrality'][name] = avg_farness_centrality
	request.session.modified = True	
	return travel_times

