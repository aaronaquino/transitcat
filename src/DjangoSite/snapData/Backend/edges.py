#!/bin/env python2
''' Code for creating a L-space graph, in which an edge connects two nodes that represent consecutive stops on the same line. '''
from __future__ import print_function
from pyproj import Geod
from utils import clean_data_frame, dist
import snap
import sys


def create_l_space_graph(G, node_dict, networks, directory_path):
    ''' Creates an L-space graph from the given node network.

        Args:
            G (TNEANet): A TNEANet containing only nodes representing stops from the given networks.
            node_dict (dict): A dict mapping stop_id to the corresponding node ID in the network.
            networks (list): The networks (madrid_metro, caltrain, etc.) to be analyzed.
            directory_path (string): The relative path to the networks being analyzed.

        Returns:
        	A TNEANet that is the L-space representation of the given networks. Note that internetwork
        	edges still need to be added.

    '''
    assert(directory_path[-1] != '/'), "directory_path should not end in a slash"

    edge_id_counter = G.GetEdges()
    for network in networks:
        stop_times_df = clean_data_frame(directory_path + '/' + network.replace(" ", ""), txt_file="stop_times.txt", sortby=None)
        trips_df = clean_data_frame(directory_path + '/' + network.replace(" ", ""), txt_file="trips.txt", sortby=None)
        num_stop_times_rows = len(stop_times_df.index)
        for i in xrange(num_stop_times_rows - 1):
            src = stop_times_df.iloc[i]
            dst = stop_times_df.iloc[i + 1]
            if src['trip_id'] == dst['trip_id'] and src['stop_sequence'] + 1 == dst['stop_sequence']:
                # These are consecutive stops.
                src_id = str(src['stop_id'])
                dst_id = str(dst['stop_id'])
                if not G.IsEdge(node_dict[src_id], node_dict[dst_id]):
                    row = trips_df.loc[trips_df['trip_id'] == src['trip_id']]
                    route_id = str(row['route_id'])
                    G.AddEdge(node_dict[src_id], node_dict[dst_id], edge_id_counter)
                    G.AddStrAttrDatE(edge_id_counter, route_id, 'route_id')
                    G.AddStrAttrDatE(edge_id_counter, src_id, 'src_stop_id')
                    G.AddStrAttrDatE(edge_id_counter, dst_id, 'dst_stop_id')
                    # print 'Adding edge from %s to %s' % (G.GetStrAttrDatN(node_dict[src_id], 'stop_name'), G.GetStrAttrDatN(node_dict[dst_id], 'stop_name'))
                    edge_id_counter += 1
                if not G.IsEdge(node_dict[dst_id], node_dict[src_id]):
                    row = trips_df.loc[trips_df['trip_id'] == dst['trip_id']]
                    route_id = str(row['route_id'])
                    G.AddEdge(node_dict[dst_id], node_dict[src_id], edge_id_counter)
                    G.AddStrAttrDatE(edge_id_counter, route_id, 'route_id')
                    G.AddStrAttrDatE(edge_id_counter, dst_id, 'src_stop_id')
                    G.AddStrAttrDatE(edge_id_counter, src_id, 'dst_stop_id')
                    edge_id_counter += 1

    snap.DelZeroDegNodes(G)
    return G


def find_close_nodes(node1, nodes, threshold, wgs84_geod):
    ''' ThreadPool worker function that determines all nodes that are within the given threshold
    from the given source node. 

        Args:
            node1 ((int, float, float, string)):
                node1[0]: The node ID.
                node1[1]: The stop's longitude.
                node1[2]: The stop's latitude.
                node1[3]: The network that the stop belongs to.
            nodes (list((int, float, float, string))): A list of all tuples corresponding to all nodes
                in the network, where each tuple has the form shown above.
            threshold (float): The threshold (meters) for determining if stops from different modes of
                transit should be connected.
            wgs84_geod (Geod): A Geod class instance used for calculating distances between points on
                the planet.

        Returns:
            A list of tuples, where each tuple consists of a source node ID and a destination node ID.

    '''
    edges = []
    for node2 in nodes:
        if (node2[0] != node1[0]
                and node2[3] != node1[3]
                and dist(node1[1], node1[2], node2[1], node2[2], wgs84_geod) < threshold):
            # Found an edge!
            edges.append((node1[0], node2[0]))
    return edges


def get_internetwork_edges(G, threshold, threads=6):
    ''' Adds internetwork edges to a graph by connecting stops from different modes of transit that
    are within the given threshold distance from one another.

        Args:
            G (TNEANet): A TNEANet representing a particular set of PTNs.
            threshold (float): The threshold (meters) for determining if stops from different modes of
                transit should be connected.
            threads (int): The number of threads to use.

        Returns:
            G (TNEANet): A TNEANet updated with its internetwork edges.
            internetwork_edges (list): A list of tuples, where each tuple consists of a source node ID
                and a destination node ID.
    '''
    wgs84_geod = Geod(ellps='WGS84')
    try:
        from multiprocessing.dummy import Pool as ThreadPool
        from functools import partial
    except ImportError:
        print('Unable to execute multithreading :(')
        return None, None

    print('Creating list of nodes and locations...', end='')
    nodes = [(node.GetId(),
              G.GetFltAttrDatN(node.GetId(), 'stop_lon'),
              G.GetFltAttrDatN(node.GetId(), 'stop_lat'),
              G.GetStrAttrDatN(node.GetId(), 'network_name'))
             for node in G.Nodes()]
    print('Done!')
    print('Starting ThreadPool with {} threads...'.format(threads), end='')
    sys.stdout.flush()
    pool = ThreadPool(threads)
    edges = pool.map(
        partial(find_close_nodes, nodes=nodes, threshold=threshold,
                wgs84_geod=wgs84_geod),
        nodes)
    pool.close()
    pool.join()
    print('Done!')
    sys.stdout.flush()

    # Add each edge to the network.
    print('Graph currently has {} edges'.format(G.GetEdges()))
    print('Adding edges to the graph...', end='')
    internetwork_edges = []
    for edge_set in edges:
        for edge in edge_set:
            G.AddEdge(edge[0], edge[1])
            internetwork_edges.append(edge)
    print('Done!')
    print('Graph now has {} edges'.format(G.GetEdges()))
    return G, internetwork_edges


