
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponseRedirect, JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import generic

from Backend.calculate_criticality import create_average_farness_centrality_files, get_criticality
from Backend.isochrone_utils import multiple_full_isochrone, multiple_full_isochrone_transitland
import Backend.main as gtfsMain
import Backend.plotting_utils as plotting
from Backend.utils import unzip_gtfs, compute_useful_graph_stats, byteify, average_lat_long
from Backend.yelp import getAllBusinessesInfo

from .models import SnapPickle
from .forms import DocumentForm

import cPickle as pickle
from datetime import datetime, date, time, timedelta
from itertools import izip_longest
from pprint import pprint
import json
import os

import time as timer

class UploadOrLoadView(generic.ListView):
    template_name = 'snapData/uploadOrLoad.html'
    context_object_name = 'latest_gtfs_list'

    def get_queryset(self):
        """Return the last five published questions."""
        return SnapPickle.objects.order_by('-pub_date')[:3]

class LoadView(generic.ListView):
    template_name = 'snapData/load.html'
    context_object_name = 'latest_gtfs_list'

    def get_queryset(self):
        """Return the last five published questions."""
        return SnapPickle.objects.order_by('-pub_date')

def detail(request, id):
    try:
        snapPickle = SnapPickle.objects.get(pk=id)
    except SnapPickle.DoesNotExist:
        raise Http404("Question does not exist")

    pprint(vars(snapPickle))
    graph, node_dict, internetwork_edges = gtfsMain.load(snapPickle.name, snapPickle.snapFileName, snapPickle.pickleFileName)
    stats = compute_useful_graph_stats(graph)

    return render(request, 'snapData/detail.html', \
        {'snapPickle': snapPickle, 'stats': stats, 'noSpacesName': snapPickle.name.replace(" ", ""), 'cleanedIds':filter(None, snapPickle.onestop_ids)})


def upload(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()

            #will get the oldest file with this name lol, need to fix
            name = form.cleaned_data.get("name", "")
            documentName = form.cleaned_data.get("document", "").name
            onestop_id = form.cleaned_data.get("onestop_id", "")

            resultsPath = "../../../Results"
            fullResultsPath = resultsPath + "/" + name.replace(" ", "") + "/"
            if not os.path.exists(fullResultsPath):
                os.makedirs(fullResultsPath)
            unzip_gtfs("../../../Data/zipFiles/" + documentName, fullResultsPath)

            snapPickle = gtfsMain.upload(name, [name], [onestop_id], resultsPath)
            return redirect('snapData:index')
    else:
        form = DocumentForm()
    return render(request, 'snapData/upload.html', {
        'form': form
    })

def map(request, id):
    try:
        snapPickle = SnapPickle.objects.get(pk=id)
    except SnapPickle.DoesNotExist:
        raise Http404("Question does not exist")
    graph, node_dict, internetwork_edges = gtfsMain.load(snapPickle.name, snapPickle.snapFileName, snapPickle.pickleFileName)
    data = {'id': id, 'name': snapPickle.name}
    data.update(average_lat_long(graph))
    data.update(plotting.getShapes(request, snapPickle.name, snapPickle.networks, filter(None, snapPickle.onestop_ids)))

    data['use_transitland'] = len(snapPickle.networks) == len(filter(None, snapPickle.onestop_ids))
    return render(request, 'snapData/mapTest.html', data)


def searchYelp(request):
    searchTerm = request.GET.get('searchTerm', None)
    searchDimensions = byteify(json.loads(request.GET.get('searchDimensions', None)))
    print searchTerm
    print searchDimensions

    data = []
    for searchDimension in searchDimensions:
        data.append(getAllBusinessesInfo(searchTerm, searchDimension, data))
    return JsonResponse({'index': request.GET.get('index', None), 'data': data})

#returns an isochrone based off a request and snappickle
def compute_isochrone(request, snapPickle, nodeLocation, weekday, hour, minute):
    graph, node_dict, internetwork_edges = gtfsMain.load(snapPickle.name, snapPickle.snapFileName, snapPickle.pickleFileName)

    # Made this a baby isochrone: 
    isochroneTimes = [10, 20, 30]
    start_timer = timer.time()
    print "computing isochrones", snapPickle.networks, filter(None, snapPickle.onestop_ids)

    # Toggle this to make it run transitland isochrone
    if len(snapPickle.networks) == len(filter(None, snapPickle.onestop_ids)):
        results = multiple_full_isochrone_transitland(filter(None, snapPickle.onestop_ids), nodeLocation, \
            weekday, hour, minute, isochroneTimes)
        print("--- %s seconds ---" % (timer.time() - start_timer))
        return results
    else:
        d = date(2018, 6, 11 + weekday)
        t = time(hour, minute)
        start_time = datetime.combine(d, t)

        RESULTS_LOCATION = "../../../Results/" + snapPickle.name.replace(" ", "") + "-AdditionalData"
        avg_farness_centrality_path = RESULTS_LOCATION + '/Travel_Times/'
        if not os.path.exists(avg_farness_centrality_path) or \
                not request.session.get('travel_times') or \
                snapPickle.name not in request.session.get('travel_times'):
            travel_times = create_average_farness_centrality_files(request, snapPickle.name, \
                graph, snapPickle.networks, node_dict, internetwork_edges)
        else:
            travel_times = request.session.get('travel_times')[snapPickle.name]

        results = multiple_full_isochrone(graph, node_dict, nodeLocation, start_time, \
            isochroneTimes, travel_times)
        print("--- %s seconds ---" % (timer.time() - start_timer))
        return results


def isochrone(request):
    id = request.GET.get('id', None)
    try:
        snapPickle = SnapPickle.objects.get(pk=id)
    except SnapPickle.DoesNotExist:
        raise Http404("Question does not exist")

    lat = float(request.GET.get('lat', None))
    lng = float(request.GET.get('lng', None))

    hour, sep, minute = request.GET.get('time', None).partition(':')
    day = int(request.GET.get('day', None))
    print time, hour, minute, day

    return JsonResponse({'isochrones': compute_isochrone(request, snapPickle, (lat, lng), day, int(hour), int(minute))})


def mapStop(request, id, stopid):
    try:
        snapPickle = SnapPickle.objects.get(pk=id)
    except SnapPickle.DoesNotExist:
        raise Http404("Question does not exist")
    graph, node_dict, internetwork_edges = gtfsMain.load(snapPickle.name, snapPickle.snapFileName, snapPickle.pickleFileName)
    data = {'id': id, 'name': snapPickle.name}
    data.update(average_lat_long(graph))
    data.update(plotting.getShapes(request, snapPickle.name, snapPickle.networks, filter(None, snapPickle.onestop_ids)))
    for node in data['nodeList']:
        if node['stop_id'] == stopid:
            data['stop'] = node

    if 'stop' not in data:
        raise Http404("Stop does not exist")

    data['dist'] = {}

    RESULTS_LOCATION = "../../../Results/" + snapPickle.name.replace(" ", "") + "-AdditionalData"
    avg_farness_centrality_path = RESULTS_LOCATION + '/Travel_Times/' + str(stopid) + '.pkl'
    if not os.path.exists(avg_farness_centrality_path) or \
            not request.session.get('travel_times') or \
            snapPickle.name not in request.session.get('travel_times'):
        travel_times = create_average_farness_centrality_files(request, snapPickle.name, graph, snapPickle.networks, node_dict, internetwork_edges)
    else:
        travel_times = request.session.get('travel_times')[snapPickle.name]
    with open(avg_farness_centrality_path, 'rb+') as input:
        dist = pickle.load(input)
        prev = pickle.load(input)
        avg_path_length = pickle.load(input)

        data['dist'] = dist
        data['avg_path_length'] = avg_path_length


    data['neighbors'] = [graph.GetStrAttrDatN(node_id, 'stop_name') for node_id in plotting.get_neighbors(graph, node_dict[stopid])]
    print data['nodeList'], data['neighbors']

    data['use_transitland'] = len(snapPickle.networks) == len(filter(None, snapPickle.onestop_ids))

    return render(request, 'snapData/mapStop.html', data)

def criticality(request):
    print request
    id = request.GET.get('graph_id', None)
    try:
        snapPickle = SnapPickle.objects.get(pk=id)
    except SnapPickle.DoesNotExist:
        raise Http404("Question does not exist")
    graph, node_dict, internetwork_edges = gtfsMain.load(snapPickle.name, snapPickle.snapFileName, snapPickle.pickleFileName)
    
    src_stop_id = request.GET.get('stop_id', None)
    dst_stop_id = request.GET.get('neighbor_id', None)
    src_node = node_dict[src_stop_id]
    dst_node = node_dict[dst_stop_id]
    dst_name = graph.GetStrAttrDatN(dst_node, 'stop_name')

    consecutive_station_times_path = "../../../Results/" + snapPickle.name.replace(" ", "") + "-AdditionalData/consecutive_station_times.pkl"
    avg_farness_centrality = request.session['avg_farness_centrality'][snapPickle.name]
    criticality = get_criticality(graph, src_node, dst_node, consecutive_station_times_path, avg_farness_centrality)

    return JsonResponse({"criticality": criticality, "neighbor_name": dst_name})

def updateFeeds(request, id):
    try:
        snapPickle = SnapPickle.objects.get(pk=id)
    except SnapPickle.DoesNotExist:
        raise Http404("Question does not exist")

    if request.method == 'POST':
        print request.POST
        new_onestop_ids = []
        for network in snapPickle.networks:
            new_id = request.POST.get(network)
            if new_id != None and len(new_id) > 0:
                new_onestop_ids.append(new_id)

        snapPickle.onestop_ids = new_onestop_ids
        snapPickle.save()

        return redirect('snapData:detail', id=id)

    else:
        netsAndIds = [list(a) for a in izip_longest(snapPickle.networks, snapPickle.onestop_ids, fillvalue="")]
        print netsAndIds
        data = {'id': id, 'name': snapPickle.name, "netsAndIds": netsAndIds}
        return render(request, 'snapData/updateFeeds.html', data)

def mergeGraphs(request, id):
    try:
        snapPickle = SnapPickle.objects.get(pk=id)
    except SnapPickle.DoesNotExist:
        raise Http404("Question does not exist")
    otherSnapPickles = SnapPickle.objects.all().exclude(pk=id)

    if request.method == 'POST':
        print request.POST
        otherNetworkNames = []
        otherOnestopIds = []
        for oSP in otherSnapPickles:
            otherNetworkName = request.POST.get(str(oSP.id))
            if otherNetworkName != None:
                otherNetworkNames = otherNetworkNames + oSP.networks
                otherOnestopIds = otherOnestopIds + oSP.onestop_ids
        if otherNetworkNames != []:
            networks = otherNetworkNames + [snapPickle.name]
            onestop_ids = otherOnestopIds + snapPickle.onestop_ids
            newName = request.POST.get('name')
            if newName == '':
                newName = '+'.join(networks)

            resultsPath = "../../../Results"
            newSnapPickle = gtfsMain.upload(newName, networks, onestop_ids, resultsPath)


        return redirect('snapData:index')
    else:
        data = {'id': id, 'name': snapPickle.name, "snapPickle": snapPickle, "otherSnapPickles": otherSnapPickles}
        return render(request, 'snapData/mergeGraphs.html', data)

