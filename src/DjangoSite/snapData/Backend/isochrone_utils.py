#!/bin/env python2
'''Utility functions for creating and rendering isochrone maps.'''
from datetime import datetime, date, time, timedelta
import json
import requests
import snap
import time as timer
from math import sin, cos, acos, radians # used for isochrone maps
from pyproj import Geod
from utils import average_lat_long, dist

NUM_RESULTS_PER_JSON_PAGE = 50



def is_valid_transitland_feed(feed_onestop_id):
	''' Checks if a given Transitland feed Onestop ID is valid.

		Args:
			feed_onestop_id (string): A Transitland feed Onestop ID.

		Returns:
			True if the ID is valid, else False.

	'''
	transitland_request_url = 'https://transit.land/api/v1/stop_stations?imported_from_feed=' + feed_onestop_id + '&per_page=1'
	print('Making request to URL: ' + transitland_request_url)
	response = requests.get(transitland_request_url)

	# 429 is ratelimiting status code - wait a bit!
	while response.status_code == 429:
		timer.sleep(1)
		response = requests.get(transitland_request_url)
	if response.status_code == 200:
		return True

	return False


def add_onestop_ids_to_network(G, feed_onestop_ids):
	''' Updates the given network so that each node contains an attribute called 'transitland_onestop_ids',
	which will be a string of comma-separated values corresponding to the Transitland Onestop IDs for that
	stop. Caltrain is an example of a network whose stops have multiple Onestop IDs, each corresponding to
	a different platform at that stop (i.e., northbound and southbound).  

		Args:
			G (TNEANet): A TNEANet representing a PTN.
			feed_onestop_ids (dict): A dictionary mapping network_name (string) to the Onestop ID (string)
				of the feed for that network. network_name is the value that associated with the 'network_name'
				attribute on a node in G.

		Returns:
			The updated TNEANet.

	'''
	for NI in G.Nodes():
		network_name = G.GetStrAttrDatN(NI.GetId(), 'network_name')
		if network_name not in feed_onestop_ids:
			raise KeyError('Network \'' + network_name + '\' not found in feed_onestop_ids.')

		feed_onestop_id = feed_onestop_ids[network_name]
		lat = str(G.GetFltAttrDatN(NI.GetId(), 'stop_lat'))
		lon = str(G.GetFltAttrDatN(NI.GetId(), 'stop_lon'))
		transitland_request_url = 'https://transit.land/api/v1/stop_stations?imported_from_feed=' + feed_onestop_id + '&lat=' + lat + '&lon=' + lon + '&r=100'
		# print('Making request to URL: ' + transitland_request_url)

		response = requests.get(transitland_request_url)

		# 429 is ratelimiting status code - wait a bit!
		while response.status_code == 429:
			timer.sleep(1)
			response = requests.get(transitland_request_url)

		if response.status_code != 200:
			raise RuntimeError('Error code ' + str(response.status_code) + ', failed to fetch StopStations information from Transitland for URL ' + transitland_request_url)

		data = response.json()
		platform_onestop_ids = []
		if len(data['stop_stations']) == 0:
			raise RuntimeError('No StopStations information found for node ID ' + str(NI.GetId()) + ' (' + G.GetStrAttrDatN(NI.GetId(), 'stop_name') + ')')

		for entry in data['stop_stations']:
			for platform in entry['stop_platforms']:
				platform_onestop_ids.append(str(platform['onestop_id']))
		concatenated_ids = ','.join(platform_onestop_ids)
		# print('Adding Onestop IDs ' + concatenated_ids + ' to station ' + G.GetStrAttrDatN(NI.GetId(), 'stop_name'))
		G.AddStrAttrDatN(NI.GetId(), concatenated_ids, 'transitland_onestop_ids')

	return G


def get_nearby_date_for_weekday(weekday, hour, minute, second=0):
	''' Generates a datetime.datetime object corresponding to the current or nearest future date
	with the given weekday and datetime characteristics.

		Args:
			weekday (int): An integer from 0-6, inclusive, where Monday is 0 and Sunday is 6.
			hour (int): An integer from 0-24, inclusive.
			minute (int): An integer from 0-59, inclusive.
			second (int): An integer from 0-59, inclusive.

		Returns:
			A datetime.datetime object, as specified above.

	'''
	today = datetime.today()
	if weekday - today.weekday() >= 0:
		result_day = today + timedelta(days=weekday - today.weekday())
	else:
		result_day = today + timedelta(days=weekday - today.weekday() + 7)
	result_day = result_day.replace(hour=hour, minute=minute, second=second, microsecond=0)

	return result_day


def get_stations_reachable_from_source(source_id, start_time, end_time, visitedURLs):
	''' Makes a Transitland API query to determine all trips leaving from a given stop
	within a given window of time. For instance, you can query which trains, if any, leave
	from the Palo Alto Caltrain station within 30 minutes of 5:00pm on a Wednesday.

		Args:
			source_id (string): The Onestop ID for this source stop.
			start_time (datetime.datetime): The start time of the window in which to search
				for departing trips.
			end_time (datetime.datetime): The end time of the window in which to search for
				departing trips.
			visitedURLs (set of strings): A set of schedule_stop_pairs urls we have queried before, 
				to avoid querying multiple times

		Returns:
			A list of (destination_id, arrival_time) pairs, where dest_node_id is the Onestop ID of
			a stop that is one stop away from the source and arrival_time is the arrival time at
			that stop, as a datetime.datetime object.

	'''
	# Check that end_time is after start_time.
	if start_time >= end_time:
		raise RuntimeError('Invalid start and/or end times for query window.')

	start_clock_time = start_time.strftime('%H:%M:%S')
	end_clock_time = end_time.strftime('%H:%M:%S')

	# Adjust if end_time occurs in next day.
	if end_time.day != start_time.day:
		end_clock_time = str(end_time.hour + 24) + end_clock_time[2:]

	calendar_date = start_time.strftime('%Y-%m-%d')
	if source_id[-1] == '<': # no platform number, use parent station instead
		source_id = source_id[:-1]
	transitland_request_url = 'https://transit.land/api/v1/schedule_stop_pairs?origin_onestop_id=' + source_id + '&origin_departure_between=' + start_clock_time + ',' + end_clock_time + '&date=' + calendar_date
	
	if transitland_request_url not in visitedURLs: #only make this query if we haven't before
		visitedURLs.add(transitland_request_url)
		print('Making request to URL: ' + transitland_request_url)

		response = requests.get(transitland_request_url)

		# 429 is ratelimiting status code - wait a bit!
		while response.status_code == 429:
			timer.sleep(1)
			response = requests.get(transitland_request_url)

		if response.status_code != 200:
			print response
			raise RuntimeError('Error code ' + str(response.status_code) + ', failed to fetch schedule information from Transitland for URL ' + transitland_request_url)

		data = response.json()
		all_reachable_stations = get_stations_reachable_from_source_helper(data, start_time, end_time)

		# Continue making API requests if there are more pages of JSON.
		page_index = 0
		while 'next' in data['meta']:
			page_index += 1
			offset = str(page_index * NUM_RESULTS_PER_JSON_PAGE)
			print('Requesting routing JSON page ' + str(page_index))
			response = requests.get(transitland_request_url + '&offset=' + offset)

			# 429 is ratelimiting status code - wait a bit!
			while response.status_code == 429:
				timer.sleep(1)
				response = requests.get(transitland_request_url + '&offset=' + offset)

			if response.status_code != 200:
				raise RuntimeError('Error code ' + str(response.status_code) + ', failed to fetch schedule information from Transitland for URL ' + transitland_request_url + ' with offset ' + offset)

			data = response.json()
			all_reachable_stations += get_stations_reachable_from_source_helper(data, start_time, end_time)

		return all_reachable_stations
	return None


def get_stations_reachable_from_source_helper(data, start_time, end_time):
	''' Helper function for get_stations_reachable_from_source() that takes a valid JSON response
	from a Transitland API call and extracts the relevant arrival information.

		Args:
			data (JSON): JSON generated from Transitland API call.
			start_time (datetime.datetime): The start time of the window in which to search
				for departing trips.
			end_time (datetime.datetime): The end time of the window in which to search for
				departing trips.

		Returns:
			A list of (destination_id, arrival_time) pairs, where dest_node_id is the Onestop ID of
			a stop that is one stop away from the source and arrival_time is the arrival time at
			that stop, as a datetime.datetime object.

	'''
	all_reachable_stations = []
	for entry in data['schedule_stop_pairs']:
		destination_id = entry['destination_onestop_id']

		# Check if we arrive the day after we left (e.g., an 11:30pm train that arrives at 12:30am).
		arrive_next_day = False
		raw_arrival_time = entry['destination_arrival_time']
		if int(raw_arrival_time[:2]) >= 24:
			arrive_next_day = True
			raw_arrival_time = str(int(raw_arrival_time[:2]) % 24) + raw_arrival_time[2:]
		arrival_time = datetime.strptime(raw_arrival_time, '%H:%M:%S')
		arrival_time = arrival_time.replace(year=start_time.year, month=start_time.month, day=start_time.day)
		if arrive_next_day:
			arrival_time = arrival_time + timedelta(days=1)

		# Only record this destination if we get there before end_time.
		if arrival_time < end_time:
			all_reachable_stations.append((destination_id, arrival_time))

	return all_reachable_stations


def compute_walking_time_between_points(lat1, lon1, lat2, lon2, walking_speed=6.0):
	''' Computes the time it takes to walk between two points (assuming a straight line) at the
	given speed.

		Args:
			lat1 (float): Latitude of the starting point.
			lon1 (float): Longitude of the starting point.
			lat2 (float): Latitude of the end point.
			lon2 (float): Longitude of the end point.
			walking_speed (float): The walking speed in kilometers per hour.

		Returns:
			A datetime.timedelta object indicating the amount of time elapsed.

	'''
	wgs84_geod = Geod(ellps='WGS84')
	distance_in_km = dist(lon1, lat1, lon2, lat2, wgs84_geod) / 1000.0
	hours_elapsed = distance_in_km / walking_speed

	return timedelta(hours=hours_elapsed)



def reachable_stops_walking_transitland(feed_onestop_id, start_coord, start_time, timespan, walking_speed=6.0):
	''' Computes the stops you can reach while walking, using the Transitland API.

		Args:
			feed_onestop_id (string): A Transitland feed Onestop ID.
			start_coord: A duple containing two floats (latitude, longitude) corresponding to the
				starting location for the isochrone analysis.
			start_time (datetime.datetime): The start time of the window in which to search
				for departing trips.
			timespan (datetime.timedelta): Object indicating the maximum time within which
				the stop should be reached.
			network (string): The network (Madrid_Metro, Caltrain, etc.)
				being analyzed.
		Optional Args:
			walking_speed (float): The walking speed in kilometers per hour.

		Returns:
			A list of dictionaries, each representing one stop, each containing:
				- stop_id (int): The Transitland Onestop ID of the stop.
				- start_time (datetime.datetime): The time we can reach that stop if walking.

	'''
	lat_start = str(start_coord[0])
	lon_start = str(start_coord[1])
	hours_of_walking = timespan.seconds / 3600.0
	radius_in_meters = str(walking_speed * 1000.0 * hours_of_walking)
	transitland_request_url = 'https://transit.land/api/v1/stop_stations?imported_from_feed=' + feed_onestop_id + '&lat=' + lat_start + '&lon=' + lon_start + '&r=' + radius_in_meters
	print('Making request to URL: ' + transitland_request_url)

	response = requests.get(transitland_request_url)

	# 429 is ratelimiting status code - wait a bit!
	while response.status_code == 429:
		timer.sleep(1)
		response = requests.get(transitland_request_url)
	if response.status_code != 200:
		raise RuntimeError('Error code ' + str(response.status_code) + ', failed to fetch StopStations information from Transitland for URL: ' + transitland_request_url)

	data = response.json()
	reachable_stops = []
	for entry in data['stop_stations']:
		for platform in entry['stop_platforms']:
			lat_end = float(platform['geometry_centroid']['coordinates'][1])
			lon_end = float(platform['geometry_centroid']['coordinates'][0])
			time_elapsed = compute_walking_time_between_points(float(lat_start), float(lon_start), lat_end, lon_end, walking_speed)
			reachable_stop = {
				'stop_id': platform['onestop_id'],
				'start_time': start_time + time_elapsed
			}
			reachable_stops.append(reachable_stop)

	# Continue making API requests if there are more pages of JSON.
	page_index = 0
	while 'next' in data['meta']:
		page_index += 1
		offset = str(page_index * NUM_RESULTS_PER_JSON_PAGE)
		response = requests.get(transitland_request_url + '&offset=' + offset)

		# 429 is ratelimiting status code - wait a bit!
		while response.status_code == 429:
			timer.sleep(1)
			response = requests.get(transitland_request_url + '&offset=' + offset)

		if response.status_code != 200:
			raise RuntimeError('Error code ' + str(response.status_code) + ', failed to fetch stop stations information from Transitland for URL ' + transitland_request_url + ' with offset ' + offset)

		data = response.json()
		reachable_stops = []
		for entry in data['stop_stations']:
			for platform in entry['stop_platforms']:
				time_elapsed = compute_walking_time_between_points(lat1, lon1, lat2, lon2, walking_speed)
				reachable_stop = {
					'stop_id': platform['onestop_id'],
					'start_time': start_time + time_elapsed
				}
				reachable_stops.append(reachable_stop)

	return reachable_stops


def calculate_distance_km(start, end):
	''' Computes the distance between two location tuples (latitude, longitude)

		Args:
			- start: a duple (type: tuple) containing (latitude, longitude)
				of the starting location
			- end: a duple (type: tuple) containing (latitude, longitude)
				of the ending location

		Returns:
			- distance between start and end in kilometers
	'''
	slat = radians(float(start[0]))
	slon = radians(float(start[1]))
	elat = radians(float(end[0]))
	elon = radians(float(end[1]))
	return 6371.01 * acos(sin(slat)*sin(elat) + cos(slat)*cos(elat)*cos(slon - elon))


def reachable_stops_walking(start_coord, start_time, timespan, G, walking_speed=6):
	''' Computes the stops you can reach while walking

		Args:
			- start_coord: a duple (type: tuple) containing (latitude, longitude)
				of the starting location
			- timespan (datetime.timedelta): object indicating the maximum time within which
				the stop should be reached
			- network (string): The network (Madrid_Metro, Caltrain, etc.)
				being analyzed.
			- G (SNAP graph): The graph to be analyzed.
		Optional Args:
			- walking speed: the walking speed of the individual in kilometers per hour

		Returns:
			- a list of dictionaries, each representing one stop, each containing
				- stop_id (int): the ID of the stop
				- stop_name (string): the name of the stop
				- start_time: the time that the stop has been reached
				- time_elapsed (datetime.timedelta): the time it takes to walk from start_coord
					to this stop
				- time_remaining (datetime.timedelta): timespan - time_elapsed
	'''
	reachable = [] # List of dicts
	stops = average_lat_long(G)['nodeList']; # List of dicts, each with stop_name, stop_id, lat, lng
	for stop in stops:
		distance = calculate_distance_km(start_coord, (stop['lat'], stop['lng']))
		hours_elapsed = distance / walking_speed
		time_elapsed = timedelta(hours=hours_elapsed)
		if (time_elapsed <= timespan):
			data = {'stop_id': stop['stop_id'], 'stop_name': stop['stop_name'],
					'start_time': start_time + time_elapsed,
					'time_elapsed': time_elapsed, 'time_remaining': timespan - time_elapsed}
			reachable.append(data)
	return reachable


def get_transitland_stops_info(feed_onestop_ids):
	''' Queries the Transitland API for stop location information for the given networks, which will help
	with calculating isochrone data.

		Args:
			feed_onestop_id (list): The Transitland feed Onestop IDs (strings) of the given networks.

		Returns:
			Three return values:
			1) A dictionary mapping Onestop IDs for platforms to the Onestop ID for their parent station.
				This helps us with plotting isochrone data, since we will be able to aggregate data for
				multiple platforms at the same station.
			2) A dictionary mapping Onestop IDs for parent stations to (float, float) tuples
				representing the locations of those stations. This helps us with preprocessing isochrone
				results.
			3) A dictionary mapping Onestop IDs for platforms to (float, float) tuples representing the
				locations of those stations. This helps us with calculating isochrone data.

	'''
	platform_to_parent_station = {}
	parent_to_location = {}
	platform_to_location = {}

	for feed_onestop_id in feed_onestop_ids:
		platform_dict, parent_location_dict, platform_location_dict = get_transitland_stops_info_single_feed(feed_onestop_id)
		platform_to_parent_station.update(platform_dict)
		parent_to_location.update(parent_location_dict)
		platform_to_location.update(platform_location_dict)

	return platform_to_parent_station, parent_to_location, platform_to_location


def get_transitland_stops_info_single_feed(feed_onestop_id):
	''' Queries the Transitland API for stop location information for the given network, which will help
	with calculating isochrone data.

		Args:
			feed_onestop_id (string): The Transitland feed Onestop ID of the given network.

		Returns:
			A tuple with three elements. The three elements are:
				1) A dictionary mapping Onestop IDs for platforms to the Onestop ID for their parent station.
					This helps us with plotting isochrone data, since we will be able to aggregate data for
					multiple platforms at the same station.
				2) A dictionary mapping Onestop IDs for parent stations to (float, float) tuples
					representing the locations of those stations. This helps us with preprocessing isochrone
					results.
				3) A dictionary mapping Onestop IDs for platforms to (float, float) tuples representing the
					locations of those stations. This helps us with calculating isochrone data.

	'''
	transitland_request_url = 'https://transit.land/api/v1/stop_stations?imported_from_feed=' + feed_onestop_id
	print('Making request to URL: ' + transitland_request_url)

	response = requests.get(transitland_request_url)

	# 429 is the rate limiting status code - wait a bit!
	while response.status_code == 429:
		timer.sleep(1)
		response = requests.get(transitland_request_url)
	if response.status_code != 200:
		raise RuntimeError('Error code ' + str(response.status_code) + ', failed to fetch StopStations information from Transitland for feed: '+ feed_onestop_id)

	data = response.json()
	platform_to_parent_station, parent_to_location, platform_to_location = get_transitland_stops_info_helper(data)

	# Continue making API requests if there are more pages of JSON.
	page_index = 0
	while 'next' in data['meta']:
		page_index += 1
		offset = str(page_index * NUM_RESULTS_PER_JSON_PAGE)
		print('Requesting StopStations JSON page ' + str(page_index))
		transitland_request_url = 'https://transit.land/api/v1/stop_stations?imported_from_feed=' + feed_onestop_id + '&offset=' + offset
		response = requests.get(transitland_request_url)

		# 429 is the rate limiting status code - wait a bit!
		while response.status_code == 429:
			timer.sleep(1)
			response = requests.get(transitland_request_url)
		if response.status_code != 200:
			raise RuntimeError('Error code ' + str(response.status_code) + ', failed to fetch StopStations information from Transitland for feed: '+ feed_onestop_id)

		data = response.json()
		platform_dict, parent_location_dict, platform_location_dict = get_transitland_stops_info_helper(data)
		platform_to_parent_station.update(platform_dict)
		parent_to_location.update(parent_location_dict)
		platform_to_location.update(platform_location_dict)

	keys = platform_to_parent_station.keys()
	for key in keys:
		if '<' in key:
			value = platform_to_parent_station[key]
			newKey, sep, tail = key.partition('<')
			platform_to_parent_station[newKey] = value

	keys = platform_to_location.keys()
	for key in keys:
		if '<' in key:
			value = platform_to_location[key]
			newKey, sep, tail = key.partition('<')
			platform_to_location[newKey] = value

	return (platform_to_parent_station, parent_to_location, platform_to_location)


def get_transitland_stops_info_helper(data):
	''' Helper function for get_transitland_stops_info() that takes a valid JSON response from a Transitland
	API call and extracts the relevant stops information.

		Args:
			data (JSON): JSON generated from Transitland API call.

		Returns:
			A tuple with three elements. The three elements are:
				1) A dictionary mapping Onestop IDs for platforms to the Onestop ID for their parent station.
					This helps us with plotting isochrone data, since we will be able to aggregate data for
					multiple platforms at the same station.
				2) A dictionary mapping Onestop IDs for parent stations to (float, float) tuples
					representing the locations of those stations. This helps us with preprocessing isochrone
					results.
				3) A dictionary mapping Onestop IDs for platforms to (float, float) tuples representing the
					locations of those stations. This helps us with calculating isochrone data.

	'''
	platform_to_parent_station = {}
	parent_to_location = {}
	platform_to_location = {}

	for entry in data['stop_stations']:
		lat = float(entry['geometry_centroid']['coordinates'][1])
		lng = float(entry['geometry_centroid']['coordinates'][0])
		stop_id = str(entry['onestop_id'])

		parent_to_location[stop_id] = (lat, lng)

		for platform in entry['stop_platforms']:
			platform_id = str(platform['onestop_id'])
			platform_to_parent_station[platform_id] = stop_id

			platform_lat = float(platform['geometry_centroid']['coordinates'][1])
			platform_lng = float(platform['geometry_centroid']['coordinates'][0])
			platform_to_location[platform_id] = (platform_lat, platform_lng)

	return (platform_to_parent_station, parent_to_location, platform_to_location)


### Using transitland API, (lat, long, distance) --> stops within that radius

def search_paths(G, node_dict, start_station, travel_times):
	''' Explores all possible stations reachable from start_station given a time constraint

		Args:
			- G: a TNEANet representing the input graph
			- node_dict: a dict mapping stop_id to the corresponding node ID in the network;
				available upon graph creation in nodes.py
			- start_station: A single dictionary containing the keys
				- stop_id: GTFS stop_id
				- start_time: a time to start from (datetime object)
				- time_remaining: the time left to travel
			- travel_times: A dictionary, where a key is of the form (src_node_id, dst_node_id) and a value is the travel
				time between those stops in seconds; obtain this using compute_consecutive_stop_times in
				calculate_shortest_paths.py

		Returns:
			- A dictionary mapping node_id's to the greatest possible time_remaining (datetime object)
			  indicating the time remaining on the clock (presumably left for walking)
	'''
	reachable = {} # Dict from node_id to time_remaining
	# Convert start_station to use node_id's instead
	start_station = {'node_id': node_dict[start_station['stop_id']],
					 'start_time': start_station['start_time'],
					 'time_remaining': start_station['time_remaining']}
	def search_paths_helper(start_station, visited):
		visited.append(start_station['node_id']); # visited keeps track of node_id's
		node_iterator = G.GetNI(start_station['node_id'])
		num_neighbors = node_iterator.GetOutDeg()
		#print("Num_neighbors: " + str(num_neighbors))
		neighbors = []
		for i in range(num_neighbors):
			neighbors.append(node_iterator.GetOutNId(i))
		#print(neighbors)
		# BASE CASE: if there's no neighbors, or we've visited all the neighbors before
		# (i.e. neighbors is a subset of visited), return
		if not neighbors or (set(neighbors) < set(visited)):
			return
		# Otherwise, keep searching
		for neighbor in neighbors:
			if neighbor not in visited:
				travel_time_seconds = travel_times[(start_station['node_id'], neighbor)]
				# If we have more time remaining than it takes to get to the neighbor, go to neighbor
				if start_station['time_remaining'] >= timedelta(seconds=travel_time_seconds):
					time_remaining = start_station['time_remaining'] - timedelta(seconds=travel_time_seconds)
					# If this traversal leaves us with the most time left on the clock, update reachable
					if neighbor not in reachable or reachable[neighbor] < time_remaining:
						reachable[neighbor] = time_remaining
					# Recurse on the neighbor
					# Pass a shallow copy of visited so that recursive calls do not alter the value
					new_start_station = {'node_id': neighbor,
										 'start_time': start_station['start_time'] + timedelta(seconds=travel_time_seconds),
										 'time_remaining': time_remaining}
					search_paths_helper(new_start_station, visited[:])
	reachable[start_station['node_id']] = start_station['time_remaining']
	search_paths_helper(start_station, []) # [] because none visited yet
	return reachable


def isochrone_stats(G, node_dict, start_stations, travel_times):
	''' Computes isochrone data

		Args:
			- G: a TNEANet representing the input graph
			- node_dict: a dict mapping stop_id to the corresponding node ID in the network;
				available upon graph creation in nodes.py
			- start_stations: A list of dictionaries, each containing the keys
				- stop_id: GTFS stop_id
				- start_time: a time to start from (datetime object)
				- time_remaining: the time left to travel
			- travel_times: A dictionary, where a key is of the form (src_node_id, dst_node_id) and a value is the travel
				time between those stops in seconds; obtain this using compute_consecutive_stop_times in
				calculate_shortest_paths.py

		Returns:
			- A dictionary mapping node_id's to the greatest possible time_remaining (datetime object)
			  indicating the time remaining on the clock (presumably left for walking)
	'''
	reachable = {} # station --> best possible time
	for station in start_stations: # Each of these must be explored independently
		reachable_single = search_paths(G, node_dict, station, travel_times)
		# Update reachable based on reachable_single such that every key
		for key in reachable_single:
			if key not in reachable:
				reachable[key] = reachable_single[key]
			elif reachable_single[key] > reachable[key]:
				reachable[key] = reachable_single[key]
	return reachable


def drawable_gtfs(G, reachable, walking_speed=6):
	''' Used for post-processing of isochrone_stats outputs.

		Args:
			- G: a TNEANet representing the input graph
			- reachable: A dictionary mapping node_id's to the greatest possible time_remaining (datetime object)
			  indicating the time remaining on the clock (presumably left for walking)
			  NOTE: this is the output of isochrone_stats
		Returns:
			- A list of tuples of the form (lat, long, radius), where latitude/longitude correspond
			  to the location of a reachable point and radius is the furthest distance in meters
			  one may reach given the time left
	'''
	# print reachable
	shapes = []
	for node_id in reachable:
		lat = G.GetFltAttrDatN(node_id, 'stop_lat')
		lng = G.GetFltAttrDatN(node_id, 'stop_lon')
		time_hours = reachable[node_id].total_seconds() / 3600
		rad = walking_speed * time_hours * 1000 # Radius in meter
		shapes.append([lat, lng, rad])
	return shapes


def drawable_transitland(platform_to_parent_station, parent_to_location, reachable, walking_speed=6):
	''' Used for post-processing of isochrone_stats outputs.

		Args:
			- platform_to_parent_station (dict): A dictionary mapping Onestop IDs for platforms to the Onestop
				ID for their parent station.
			- parent_to_location (dict): A dictionary mapping Onestop IDs for parent stations to (float, float)
				tuples representing the latitude and longitude of those stations.
			- reachable (dict): A dictionary mapping platform Onestop IDs to the greatest possible time_remaining
				(datetime object) indicating the time remaining on the clock (presumably left for walking). NOTE:
				this is the output of isochrone_stats.
		Returns:
			- A list of the form [lat, lng, radius], where latitude/longitude correspond to the location
				of a reachable point and radius is the furthest distance in meters one may reach given the time left.
	'''
	parent_station_to_radius = {}
	for onestop_id in reachable:
		parent_station_id = platform_to_parent_station[onestop_id]
		time_hours = reachable[onestop_id].total_seconds() / 3600
		radius = walking_speed * time_hours * 1000 # Radius in meters.

		# Record isochrone data if we haven't seen a platform at this station yet, or if this platform is better
		# (i.e., we can move a larger radius away) than the existing one.
		if parent_station_id not in parent_station_to_radius or parent_station_to_radius[parent_station_id] < radius:
			parent_station_to_radius[parent_station_id] = radius

	shapes = []
	for parent_station_id, radius in parent_station_to_radius.iteritems():
		parent_location = parent_to_location[parent_station_id]
		lat = parent_location[0]
		lng = parent_location[1]
		shapes.append([lat, lng, radius])

	return shapes


def start_position_reachable_area(start_coord, timespan, walking_speed=6):
	''' Determines the area that is reachable by solely walking from the start position

		Args:
			- start_coord: a duple (type: tuple) containing (latitude, longitude)
				of the starting location
			- timespan (datetime.timedelta): object indicating the maximum time within which
				the stop should be reached
			- walking_speed (float): The walking speed in kilometers per hour.

		Returns:
			- A list of tuples of the form (lat, long, radius), where latitude/longitude correspond
			  to the location of a reachable point and radius is the furthest distance in meters
			  one may reach given the time left. Although there is only one tuple returned, it is put
			  inside a list for easy concatenation with other isochrone results.

	'''
	return [[float(start_coord[0]), float(start_coord[1]), timespan.total_seconds() / 3600 * walking_speed * 1000]]


def full_isochrone(G, node_dict, start_coord, start_time, timespan, json_travel_times):
	''' Used for post-processing of isochrone_stats outputs

		Args:
			- G: a TNEANet representing the input graph
			- node_dict: a dict mapping stop_id to the corresponding node ID in the network;
				available upon graph creation in nodes.py
			- start_coord: a duple (type: tuple) containing (latitude, longitude)
				of the starting location
			- start_time: a datetime object indicating the starting time for calculating
				the isochrone output
			- timespan (datetime.timedelta): object indicating the maximum time within which
				the stop should be reached
			- travel_times: A dictionary, where a key is of the form (src_node_id, dst_node_id) and a value is the travel
				time between those stops in seconds
				NOTE: obtain this using compute_consecutive_stop_times in
				calculate_shortest_paths.py

		Returns:
			- A list of tuples of the form (lat, long, radius), where latitude/longitude correspond
				to the location of a reachable point
	'''
	travel_times = {}
	bad_travel_times = json.loads(json_travel_times)
	for d in bad_travel_times:
		key = (d["key"][0], d["key"][1])
		travel_times[key] = d["value"]
	reachable_walking = reachable_stops_walking(start_coord, start_time, timespan, G)
	reachable_full = isochrone_stats(G, node_dict, reachable_walking, travel_times)
	return drawable_gtfs(G, reachable_full) + start_position_reachable_area(start_coord, timespan)

def multiple_full_isochrone(graph, node_dict, start_coord, start_time, timespans, json_travel_times):
	''' Used for post-processing of isochrone_stats outputs

		Args:
			- G: a TNEANet representing the input graph
			- node_dict: a dict mapping stop_id to the corresponding node ID in the network;
				available upon graph creation in nodes.py
			- start_coord: a duple (type: tuple) containing (latitude, longitude)
				of the starting location
			- start_time: a datetime object indicating the starting time for calculating
				the isochrone output
			- timespans (list of numbers): list indicating the maximum times within which
				the stop should be reached
			- travel_times: A dictionary, where a key is of the form (src_node_id, dst_node_id) and a value is the travel
				time between those stops in seconds
				NOTE: obtain this using compute_consecutive_stop_times in
				calculate_shortest_paths.py

		Returns:
			- A list of list of lists of the form [lat, long, radius], where latitude/longitude correspond
				to the location of a reachable point
	'''
	walking_speed = 6.0 # in km/hr

	timespans.sort()
	maxTimespan = timespans[-1]

	isochrones = range(len(timespans))
	isochrones[-1] = full_isochrone(graph, node_dict, start_coord, start_time, \
            timedelta(minutes=maxTimespan), json_travel_times)
	
	for i in range(len(timespans) - 1):
		diff_time = maxTimespan - timespans[i]
		diff_meters = diff_time / 60.0 * walking_speed * 1000
		isochrone = []
		for arr in isochrones[-1]:
			newRadius = arr[2] - diff_meters
			if newRadius > 0:
				isochrone.append([arr[0], arr[1], newRadius])
		isochrones[i] = isochrone
	return isochrones



############################
### TRANSITLAND VERSIONS ###
############################

def search_paths_transitland(feed_onestop_ids, start_station, end_time, platform_to_location, visitedURLs):
	''' Explores all possible stations reachable from start_station given a time constraint

		Args:
			- feed_onestop_ids (string): A list of Transitland feed Onestop IDs. (a list of feeds)
			- start_station: a dictionary containing the keys:
				- stop_id: the Onestop ID of that station
				- start_time: a time to start from (datetime.datetime)
			- end_time: the time by which all traversals must be completed (datetime.datetime)
			- platform_to_location (dict): A dictionary mapping Onestop IDs for platforms to (float, float) tuples
				representing the locations of those stations. This helps us with calculating isochrone data.
			- visitedURLs: A set of schedule_stop_pairs urls we have queried before, to avoid querying
				multiple times

		Returns:
			- A dictionary mapping node_id's to the greatest possible time_remaining (datetime object)
			  indicating the time remaining on the clock (presumably left for walking)
	'''
	reachable = {} # Dict from Onestop ID to time_remaining
	start_station = {'stop_id': start_station['stop_id'],
					 'start_time': start_station['start_time'],
					 'time_remaining': end_time - start_station['start_time']}
	def search_paths_helper_transitland(start_station, visited, visitedURLs):
		visited.append(start_station['stop_id'])

		# First, get all neighbors_and_arrivals reachable directly by public transit paths from the current station
		neighbors_and_arrivals = get_stations_reachable_from_source(start_station['stop_id'],
																	start_station['start_time'],
																	end_time,
																	visitedURLs)
		# get_stations_reachable_from_source returns:
		# 	A list of (destination_id, arrival_time) pairs, where dest_node_id is the Onestop ID of
		# 	a stop that is one stop away from the source and arrival_time is the arrival time at
		# 	that stop, as a datetime.datetime object.

		###
		# ADD TO NEIGHBORS AND ARRIVALS:
		# every station walkable from the current station
		if neighbors_and_arrivals != None: # if we have not done this query before
			reachable_walking = []
			for feed in feed_onestop_ids:
				reachable_walking += reachable_stops_walking_transitland(feed, platform_to_location[start_station['stop_id']],
																		 start_station['start_time'], start_station['time_remaining'])
			# reachable_walking is a A list of dictionaries, each representing one stop, each containing:
			# stop_id (int): The Transitland Onestop ID of the stop.
			# start_time (datetime.datetime): The time we can reach that stop if walking.
			# Now, convert reachable_walking into a list of (dest_id, arrival_time) tuples for concatenation with
			# neighbors_and_arrivals
			for elem in reachable_walking:
				neighbors_and_arrivals.append((elem['stop_id'], elem['start_time']))
			###

			neighbors = [pair[0] for pair in neighbors_and_arrivals]
			# BASE CASE: if there's no neighbors, or we've visited all the neighbors before
			if not neighbors or (set(neighbors) < set(visited)): # (i.e. neighbors is a subset of visited)
				return
			# Otherwise, keep searching
			for neighbor_tuple in neighbors_and_arrivals:
				neighbor = neighbor_tuple[0]
				if neighbor not in visited: # Just the neighbor, not the pair with arrival
					travel_time = neighbor_tuple[1] - start_station['start_time']
					# If we have more time remaining than it takes to get to the neighbor, go to neighbor
					if start_station['time_remaining'] >= travel_time:
						new_time_remaining = start_station['time_remaining'] - travel_time
						# If this traversal leaves us with the most time left on the clock, update reachable
						if neighbor not in reachable or reachable[neighbor] < new_time_remaining:
							reachable[neighbor] = new_time_remaining
						# Recurse on the neighbor
						# Pass a shallow copy of visited so that recursive calls do not alter the value
						new_start_station = {'stop_id': neighbor,
											 'start_time': start_station['start_time'] + travel_time,
											 'time_remaining': new_time_remaining}
						search_paths_helper_transitland(new_start_station, visited[:], visitedURLs)
	reachable[start_station['stop_id']] = start_station['time_remaining']
	search_paths_helper_transitland(start_station, [], visitedURLs) # [] because none visited yet
	return reachable


def isochrone_stats_transitland(feed_onestop_ids, start_stations, end_time, platform_to_location):
	''' Computes isochrone data, this time for transitland

		Args:
			- feed_onestop_ids (string): A list of Transitland feed Onestop IDs. (a list of feeds)
			- start_stations: A list of dictionaries, each containing the keys
				- stop_id: the Onestop ID of that station
				- start_time: a time to start from (datetime object)
			- end_time: the time by which all traversals must be completed
			- platform_to_location (dict): A dictionary mapping Onestop IDs for platforms to (float, float) tuples
				representing the locations of those stations. This helps us with calculating isochrone data.

		Returns:
			- A dictionary mapping node_id's to the greatest possible time_remaining (datetime object)
			  indicating the time remaining on the clock (presumably left for walking)
	'''
	reachable = {} # station --> best possible time
	visitedURLs = set()
	for station in start_stations: # Each of these must be explored independently
		reachable_single = search_paths_transitland(feed_onestop_ids, station, end_time, platform_to_location, visitedURLs)
		# Update reachable based on reachable_single such that every key
		for key in reachable_single:
			if key not in reachable:
				reachable[key] = reachable_single[key]
			elif reachable_single[key] > reachable[key]:
				reachable[key] = reachable_single[key]
	return reachable


def full_isochrone_transitland(feed_onestop_ids, start_coord, weekday, hour, minute, timespan):
	''' Compute isochrone plotting data using the Transitland API.

		Args:
			feed_onestop_ids (string): A list of Transitland feed Onestop IDs. (a list of feeds)
			platform_to_parent_station (dict): A dictionary mapping Onestop IDs for platforms to the Onestop
				ID for their parent station.
			parent_to_location (dict): A dictionary mapping Onestop IDs for parent stations to (float, float)
				tuples representing the latitude and longitude of those stations.
			platform_to_location (dict): A dictionary mapping Onestop IDs for platforms to (float, float) tuples
				representing the locations of those stations. This helps us with calculating isochrone data.
			start_coord: A duple containing two floats (latitude, longitude) corresponding to the
				starting location for the isochrone analysis.
			weekday (int): An integer from 0-6, inclusive, where Monday is 0 and Sunday is 6.
			hour (int): An integer from 0-24, inclusive.
			minute (int): An integer from 0-59, inclusive.
			timespan (datetime.timedelta): Object indicating the maximum time within which the stop should be
				reached.

		Returns:
			A list of lists of the form [lat, lng, radius], where latitude/longitude correspond
				to the location of a reachable point.

	'''
	start_time = get_nearby_date_for_weekday(weekday, hour, minute, 0)
	
	# platform_to_parent_station (dict): A dictionary mapping Onestop IDs for platforms to the Onestop
	# 	ID for their parent station.
	# parent_to_location (dict): A dictionary mapping Onestop IDs for parent stations to (float, float)
	# 	tuples representing the latitude and longitude of those stations.
	# platform_to_location (dict): A dictionary mapping Onestop IDs for platforms to (float, float) tuples
	# 	representing the locations of those stations. This helps us with calculating isochrone data.
	platform_to_parent_station, parent_to_location, platform_to_location = get_transitland_stops_info(feed_onestop_ids)
	reachable_walking = []
	for feed in feed_onestop_ids:
		reachable_walking += reachable_stops_walking_transitland(feed, start_coord, start_time, timespan)
	reachable_full = isochrone_stats_transitland(feed_onestop_ids, reachable_walking, start_time + timespan, platform_to_location)
	return drawable_transitland(platform_to_parent_station, parent_to_location, reachable_full) + start_position_reachable_area(start_coord, timespan)

def multiple_full_isochrone_transitland(feed_onestop_ids, start_coord, weekday, hour, minute, timespans):
	''' Compute multiple isochrone plotting data using the Transitland API.

		Args:
			feed_onestop_ids (string): A list of Transitland feed Onestop IDs. (a list of feeds)
			platform_to_parent_station (dict): A dictionary mapping Onestop IDs for platforms to the Onestop
				ID for their parent station.
			parent_to_location (dict): A dictionary mapping Onestop IDs for parent stations to (float, float)
				tuples representing the latitude and longitude of those stations.
			platform_to_location (dict): A dictionary mapping Onestop IDs for platforms to (float, float) tuples
				representing the locations of those stations. This helps us with calculating isochrone data.
			start_coord: A duple containing two floats (latitude, longitude) corresponding to the
				starting location for the isochrone analysis.
			weekday (int): An integer from 0-6, inclusive, where Monday is 0 and Sunday is 6.
			hour (int): An integer from 0-24, inclusive.
			minute (int): An integer from 0-59, inclusive.
			timespans (list of numbers): list indicating the maximum times within which the stop should be
				reached.

		Returns:
			A list of list of lists of the form [lat, lng, radius], where latitude/longitude correspond
				to the location of a reachable point.
	'''
	walking_speed = 6.0 # in km/hr

	timespans.sort()
	maxTimespan = timespans[-1]

	isochrones = range(len(timespans))
	isochrones[-1] = full_isochrone_transitland(feed_onestop_ids, start_coord, weekday, hour, minute, timedelta(minutes=maxTimespan))
	
	for i in range(len(timespans) - 1):
		diff_time = maxTimespan - timespans[i]
		diff_meters = diff_time / 60.0 * walking_speed * 1000
		isochrone = []
		for arr in isochrones[-1]:
			newRadius = arr[2] - diff_meters
			if newRadius > 0:
				isochrone.append([arr[0], arr[1], newRadius])
		isochrones[i] = isochrone
	return isochrones

