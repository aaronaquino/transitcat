#!/bin/env python2
"""Functions for creating a network of nodes (but no edges) from GTFS data."""
import snap
from utils import clean_data_frame, create_stops_to_routes_map


def update_routes(G, nid, row, stops_to_routes_map):
    ''' Adds an attribute to the given node indicating all the routes that that node services.

        Args:
            G (TNEANet): A TNEANet containing only nodes representing stops from the given networks.
            row: A row from stops.txt corresponding to the given node.
            stops_to_routes_map (dict): A dict mapping stop_name to a list of the route_ids that that stop is
                part of.
            nid (int): The node's ID.

    '''
    possible_routes = stops_to_routes_map[row['stop_name']]
    routes_concatenated = ','.join(str(x) for x in possible_routes)
    G.AddStrAttrDatN(nid, routes_concatenated, 'routes')


def create_node_network(networks, directory_path):
    ''' Create a node network with no edges given the stops.txt file as a
    dataframe from GTFS Data.

        Args:
            networks (list): The networks (madrid_metro, caltrain, etc.) to be analyzed.
            directory_path (string): File path to the directory containing the networks being analyzed.

        Returns:
            G (TNEANet): A TNEANet containing only nodes representing stops from the given networks.
            node_dict (dict): A dict mapping stop_id to the corresponding node ID in the network.
    '''
    assert(directory_path[-1] != '/'), "directory_path should not end in a slash"

    G = snap.TNEANet.New()
    node_dict = {}		# stop_id => nid
    curr_nid = 0
    for i, network in enumerate(networks):
    	# Keep track of when transfers occur.
    	stops_to_routes_map = create_stops_to_routes_map(directory_path + '/' + network.replace(" ", ""))

        # Create a node for each valid stop_id, along with relevant station information.
        stops_df = clean_data_frame(directory_path + '/' + network.replace(" ", ""), txt_file='stops.txt', sortby=None)
        stop_names = {}     # stop_name => node ID
        for index, row in stops_df.iterrows():
            if 'location_type' not in row or row['location_type'] is None or int(row['location_type']) == 0:
                stop_id = str(row['stop_id'])
                stop_name = str(row['stop_name'])
                if stop_name in stop_names.keys():
                    # We've seen this station already but as part of a different line.
                    node_dict[stop_id] = stop_names[stop_name]
                else:
                    stop_names[stop_name] = curr_nid
                    node_dict[stop_id] = curr_nid

                    try:
                        G.AddNode(curr_nid)
                    except RuntimeError:
                        import pdb
                        pdb.set_trace()

                    G.AddStrAttrDatN(curr_nid, str(stop_id), 'stop_id')
                    if 'stop_code' in row:
                        G.AddStrAttrDatN(curr_nid, str(row['stop_code']), 'stop_code')
                    else:
                        G.AddStrAttrDatN(curr_nid, str(stop_id), 'stop_code')
                    G.AddFltAttrDatN(curr_nid, row['stop_lat'], 'stop_lat')
                    G.AddFltAttrDatN(curr_nid, row['stop_lon'], 'stop_lon')
                    G.AddStrAttrDatN(curr_nid, str(row['stop_name']), 'stop_name')
                    G.AddStrAttrDatN(curr_nid, str(network), 'network_name')

                    if row['stop_name'] in stops_to_routes_map:
                        update_routes(G, curr_nid, row, stops_to_routes_map)
                    curr_nid += 1

    return G, node_dict
