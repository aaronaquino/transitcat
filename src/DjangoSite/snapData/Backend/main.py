#!/bin/env python2
import cPickle as pickle
import snap
import os
from nodes import create_node_network
from edges import create_l_space_graph, get_internetwork_edges
from utils import save_graph, load_graph

from django.utils import timezone

from ..models import SnapPickle


def upload(name, networks, onestop_ids, directoryPath):
    G, node_dict = create_node_network(networks, directoryPath)

    # Verify that nodes were created properly.
    # for NI in G.Nodes():
    # 	nodeID = NI.GetId()
    # 	print 'Node ID %d, stop_id %s, stop_name %s, stop_code %s, stop_lat %f, stop_lon %f, network_name %s' % (nodeID, G.GetStrAttrDatN(NI, 'stop_id'), G.GetStrAttrDatN(NI, 'stop_name'), G.GetStrAttrDatN(NI, 'stop_code'), G.GetFltAttrDatN(NI, 'stop_lat'), G.GetFltAttrDatN(NI, 'stop_lon'), G.GetStrAttrDatN(NI, 'network_name'))
    	# print 'Node ID %d, stop_name %s, routes %s' % (nodeID, G.GetStrAttrDatN(NI, 'stop_name'), G.GetStrAttrDatN(NI, 'routes'))

    G = create_l_space_graph(G, node_dict, networks, directoryPath)
    G, internetwork_edges = get_internetwork_edges(G, 100)

    snapFileName = "snapData/uploads/" + name.replace(" ", "") + '.graph'
    pickleFileName = "snapData/uploads/" + name.replace(" ", "") + '.pkl'
    print snapFileName
    print pickleFileName
    try:
        print('Saving graph...')
        save_graph(G, snapFileName)
        with open(pickleFileName, 'wb+') as output:
            pickle.dump(node_dict, output, pickle.HIGHEST_PROTOCOL)
            pickle.dump(internetwork_edges, output, pickle.HIGHEST_PROTOCOL)
        print('Done!')

        snapPickle = SnapPickle(name=name, 
            networks=networks,
            onestop_ids=onestop_ids,
            pub_date=timezone.now(), 
            snapFileName=snapFileName, 
            pickleFileName=pickleFileName)
        snapPickle.save()
        return snapPickle
    except IOError:
        print('Could not save node network!')

def load(graphName, snapFileName, pickleFileName):
    print "hi"
    try:
        G = load_graph(snapFileName)
        with open(pickleFileName, 'rb+') as input:
            node_dict = pickle.load(input)
            internetwork_edges = pickle.load(input)
        print('Done!')
        print node_dict
        print type(G)

        filename, fileextension = os.path.splitext(snapFileName)

        imageFilePath = "snapData/static/graphimages/" + graphName.replace(" ", "") + ".png"
        if not os.path.isfile(imageFilePath):
            snap.DrawGViz(G, 
                snap.gvlSfdp, 
                imageFilePath, 
                "Graph of " + graphName, 
                True)

        print G, node_dict, internetwork_edges
    except IOError:
        print('Could not save node network!')

    return G, node_dict, internetwork_edges
#load("JATRAN", "snapData/uploads/l_space.graph", "snapData/uploads/l_space.pkl")

