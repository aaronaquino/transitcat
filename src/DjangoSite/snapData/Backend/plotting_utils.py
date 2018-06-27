#!/bin/env python2
'''Utility functions for plotting routes and stops on a real-world map.'''
from utils import clean_data_frame
import os.path
import requests
import snap
import time

NUM_RESULTS_PER_JSON_PAGE = 50


def does_shapes_info_exist(directory_path):
	''' Checks if a shapes.txt GTFS file exists for the given network.

		Args:
			directory_path (string): The relative path to the network (madrid_metro,
				caltrain, etc.) being analyzed.

		Returns:
			True if shapes.txt exists, else false.

	'''
	return os.path.isfile(directory_path + '/shapes.txt')


def get_shapes_info(directory_path):
	''' Gets information for plotting the shapes for a given network, if that information
	is available.

		Args:
			directory_path (string): The relative path to the network (madrid_metro,
				caltrain, etc.) being analyzed.

		Returns:
			A list of dictionaries, where each object has:
				- coordinates (list): A list of dictionaries, where each object has:
					- lat (string): The latitude of a point to be plotted.
					- lng (string): The longitude of a point to be plotted.
				- color (string): A default color of 'FF0000', since GTFS data does not
					contain easily accessible color information.

	'''
	if not does_shapes_info_exist(directory_path):
		raise IOError('No shapes.txt file found for this network.')

	all_shapes_info = []
	shapes_df = clean_data_frame(directory_path, txt_file='shapes.txt', sortby=None)
	current_shape = None
	coordinates = []
	for i, e in shapes_df.iterrows():
		if str(e['shape_id']) != current_shape:
			if current_shape is not None:
				all_shapes_info.append({'coordinates': coordinates, 'color': 'FF0000'})
				coordinates = []
			current_shape = str(e['shape_id'])
		latitude = str(e['shape_pt_lat'])
		longitude = str(e['shape_pt_lon'])
		coordinates.append({'lat': latitude, 'lng': longitude})

	return all_shapes_info


def get_transitland_shapes_info(feed_onestop_id):
	''' Queries the Transitland API for information for plotting the shapes for a given network.

		Args:
			feed_onestop_id (string): The Onestop ID of the feed for the network to be plotted.

		Returns:
			A list of dictionaries, where each object has:
				- coordinates (list): A list of dictionaries, where each object has:
					- lat (string): The latitude of a point to be plotted.
					- lng (string): The longitude of a point to be plotted.
				- color (string): A hexadecimal representation of a color, without the leading '#'.

	'''
	all_shapes_info = []

	# Continue making API requests if there are more pages of JSON.
	page_index = 0
	data = {'meta': {'next': ''}}
	while 'next' in data['meta']:
		offset = str(page_index * NUM_RESULTS_PER_JSON_PAGE)
		print('Requesting routing JSON page ' + str(page_index))
		url = 'https://transit.land/api/v1/routes?imported_from_feed=' + feed_onestop_id + '&offset=' + offset
		response = requests.get(url)

		# 429 is ratelimiting status code - wait a bit!
		while response.status_code == 429:
			time.sleep(1)
			response = requests.get(url)
		if response.status_code != 200:
			raise RuntimeError('Failed to fetch shape information from Transitland for feed '+ feed_onestop_id + ' with offset ' + offset)

		data = response.json()
		for entry in data['routes']:
			for mini_shape in entry['geometry']['coordinates']:
				coordinates = []
				for coords in mini_shape:
					latitude = str(coords[1])
					longitude = str(coords[0])
					
					coordinates.append({'lat': latitude, 'lng': longitude})
				shape_info = {'coordinates': coordinates, 'color': str(entry['color'])}
				all_shapes_info.append(shape_info)
		page_index += 1

	return all_shapes_info


# Test code.

# print(does_shapes_info_exist('../../../../../Data/madrid_metro'))
# result = get_shapes_info('../../../../../Data/madrid_metro')
# print(len(result))

def get_neighbors(G, node_id):
	'''
	Args:
		- G: The Graph object 
		- node_id: the node_id of the node you want to get the neighbors of
	Returns:
		- A list of all neighbors, each represented with a node_id (integer)
	'''
	node_iterator = G.GetNI(node_id)
	num_neighbors = node_iterator.GetOutDeg()
	neighbors = []
	for i in range(num_neighbors):
		neighbors.append(node_iterator.GetOutNId(i))
	return neighbors


def getShapes(request, name, networks, feed_onestop_ids):
	if request.session.get('shapes') == None:
		request.session['shapes'] = {}
	if request.session.get('shapes').get(name) != None:
		return {'routes': request.session.get('shapes')[name]}

	all_shapes_info = []
	use_transitland = len(networks) == len(filter(None, feed_onestop_ids))
	print networks, feed_onestop_ids, use_transitland
	print "use_transitland", use_transitland, networks, feed_onestop_ids
	if use_transitland:
		try:
			for onestop_id in feed_onestop_ids:
				all_shapes_info = all_shapes_info + get_transitland_shapes_info(onestop_id)
			print "successfully fetched from transitland"
		except Exception, e:
			print e
			use_transitland = False
	if not use_transitland:
		all_shapes_info = []
		resultsPath = "../../../Results"

		for network in networks:
			fullResultsShapePath = resultsPath + "/" + network
			if does_shapes_info_exist(fullResultsShapePath):
				all_shapes_info = all_shapes_info + get_shapes_info(fullResultsShapePath)
	request.session['shapes'][name] = all_shapes_info
	request.session.modified = True	
	print request.session.get('shapes')[name]
	return {'routes': request.session.get('shapes')[name]}
