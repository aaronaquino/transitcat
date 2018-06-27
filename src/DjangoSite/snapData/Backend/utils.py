#!/bin/env python2
'''Utility functions for cleaning data frames, mapping stops to routes, and saving/loading graphs.'''
import json
import numpy as np
import pandas as pd
import snap
import zipfile
import datetime # used for isochrone maps
from math import sin, cos, acos, radians # used for isochrone maps



def byteify(input):
    '''
    Turns all unicode strings in a JSON dict to normal strings.
    '''
    if isinstance(input, dict):
        return {byteify(key): byteify(value)
                for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input


def clean_data_frame(directory_path, txt_file, sortby):
    assert(directory_path[-1] != '/'), "directory_path should not end in a slash"

    df = pd.read_csv(directory_path + '/' + txt_file)
    if sortby is not None:
        df.sort_values(sortby, inplace=True)
    return df


def create_trip_id_map(directory_path):
    ''' Creates and returns a dictionary mapping trip_id to route_id (i.e., the
    metro line). Uses the values found in trips.txt.

        Args:
            directory_path (string): The relative path to the network (madrid_metro,
                caltrain, etc.) being analyzed.

        Returns:
            A dict mapping trip_id to route_id.
    '''
    trips_df = clean_data_frame(directory_path, txt_file='trips.txt', sortby=None)
    result = {}
    for i, e in trips_df.iterrows():
        result[e['trip_id']] = e['route_id']
    return result


def create_stop_id_to_name_map(directory_path):
    ''' Creates and returns a dictionary mapping stop_id to stop_name. Uses the
    values found in stops.txt.

        Args:
            directory_path (string): The relative path to the network (madrid_metro,
                caltrain, etc.) being analyzed.

        Returns:
            A dict mapping stop_id to stop_name.

    '''
    stops_df = clean_data_frame(directory_path, txt_file='stops.txt', sortby=None)
    result = {}
    for i, e in stops_df.iterrows():
        if 'location_type' not in e or e['location_type'] is None or int(e['location_type']) == 0:
            result[e['stop_id']] = e['stop_name']
    return result


def create_stops_to_routes_map(directory_path):
    ''' Creates a dict mapping stop_name to a list of the route_ids that
    that stop is part of.

        Args:
            directory_path (string): The relative path to the network (madrid_metro,
                caltrain, etc.) being analyzed.

        Returns:
            A dict mapping stop_name to a list of the route_ids that that stop is
            part of.

    '''
    trip_id_map = create_trip_id_map(directory_path)
    stop_id_to_name_map = create_stop_id_to_name_map(directory_path)
    stop_times_df = clean_data_frame(directory_path, txt_file='stop_times.txt', sortby=None)

    result = {}
    for i, e in stop_times_df.iterrows():
        name = stop_id_to_name_map[e['stop_id']]
        route = trip_id_map[e['trip_id']]
        if name not in result:
            result[name] = [route]
        elif route not in result[name]:
            result[name].append(route)

    return result


def dist(lon1, lat1, lon2, lat2, g):
    ''' Computes the distance between two coordinates. '''
    return g.inv(lon1, lat1, lon2, lat2)[-1]


class Stats:
    def __init__(self, num_nodes, num_edges, min_degree, max_degree, avg_degree, avg_clust_coeff):
        self.num_nodes = num_nodes
        self.num_edges = num_edges
        self.min_degree = min_degree
        self.max_degree = max_degree
        self.avg_degree = avg_degree
        self.avg_clust_coeff = avg_clust_coeff        


def compute_useful_graph_stats(G):
    ''' Computes useful numerical properties for the given graph.

        Args:
            G (SNAP graph): The graph to be analyzed.

        Returns:
            A Stats object containing the following properties:
                - num_nodes
                - num_edges
                - min_degree
                - max_degree
                - avg_degree
                - avg_clust_coeff

    '''

    DegToCntV = snap.TIntPrV()
    snap.GetDegCnt(G, DegToCntV)
    degrees = np.asarray([pair.GetVal1() for pair in DegToCntV])
    print G.GetEdges()

    min_degree= np.min(degrees)
    max_degree = np.max(degrees)
    avg_degree = np.sum(np.asarray([pair.GetVal1() * pair.GetVal2() for pair in DegToCntV])) * 1.0 / G.GetNodes()

    # See more information at: https://en.wikipedia.org/wiki/Clustering_coefficient.
    avg_clust_coeff = snap.GetClustCf(G, -1)

    return Stats(num_nodes=G.GetNodes(),
                 num_edges=G.GetEdges(),
                 min_degree=min_degree,
                 max_degree=max_degree,
                 avg_degree=round(avg_degree, 3),
                 avg_clust_coeff=round(avg_clust_coeff, 3))


def average_lat_long(G):
	''' Computes the average latitude/longitude for a graph and lists nodes.

        Args:
            G (SNAP graph): The graph to be analyzed.

        Returns:
            A dictionary with the following properties
                - avgLat: the average latitude for all nodes in G
                - avgLng: the average longitude for all nodes in G
                - nodeList: a list of dictionaries for each node containing
                	- lat: latitude of node
                	- lng: longitude of node
                	- stop_name: name of node (eg. "College Park")
    '''
	nodeList = []
	totLat = 0.0
	totLng = 0.0
	for node in G.Nodes():
		stop_name = G.GetStrAttrDatN(node, 'stop_name')
		stop_id = G.GetStrAttrDatN(node, 'stop_id')
		lat = G.GetFltAttrDatN(node, 'stop_lat')
		lng = G.GetFltAttrDatN(node, 'stop_lon')
		totLat += lat
		totLng += lng
		nodeDict = {'stop_name':stop_name, 'stop_id':stop_id, 'lat': lat, 'lng': lng}
		nodeList.append(nodeDict)
	avgLat = totLat / G.GetNodes()
	avgLng = totLng / G.GetNodes()
	return {'avgLat': avgLat, 'avgLng': avgLng, 'nodeList': nodeList}


def save_graph(G, graph_file):
    ''' Saves the graph to the given location.

        Args:
            G (SNAP graph): The graph to be saved.
            graph_file (string): Location where graph should be saved.

        Returns:
            0 if successful, else 1.

    '''
    try:
        FOut = snap.TFOut(graph_file)
        G.Save(FOut)
        FOut.Flush()
        return 0
    except IOError:
        print('Could not save graph file {}'.format(graph_file))
        return 1
    print('An error occured')
    return 1


def load_graph(graph_file):
    ''' Loads a previously saved graph from the given location.

        Args:
            graph_file (string): Location where graph was saved.

        Returns:
            The SNAP graph that was loaded, else None.

    '''
    try:
        FIn = snap.TFIn(graph_file)
        G = snap.TNEANet.Load(FIn)
        return G
    except IOError:
        print('Could not load graph file {}'.format(graph_file))
        return None
    print('An error occured')
    return None


def unzip_gtfs(source, dest):
    ''' Unzips a zipped GTFS data set.

        Args:
            source (string): Location where the GTFS zip file is located.
            dest (string): Location where the unzipped contents should be saved.

    '''
    zip_ref = zipfile.ZipFile(source, 'r')
    zip_ref.extractall(dest)
    zip_ref.close()

