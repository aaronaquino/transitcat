import requests
import time
from utils import byteify

def addBusinessesToDict(businesses, maxDistance, d):
    '''
    Helper function for getBusinessesInfo. Adds all given business entries to the dictionary that
    will be returned by getBusinessesInfo. Each business entry is a map from the business id to
    a dictionary containing the business name, latitude, longitude, and distance as described 
    in getBusinessesInfo.

    Args:
        businesses (a JSON list): the returned list of Yelp businesses from a Yelp query
        maxDistance (int): the max distance in meters a business should be
        d (a dictionary): the dictionary to populate
    '''
    for business in businesses:
        # we don't want to include permanently closed businesses, so is_closed must be False
        # we also check to make sure the physical location is less than maxDistance - yelp checks for
        # places that serve (like deliver) to a given coordinate as well as physical locations within
        # the given radius
        if not business["is_closed"] and business["distance"] < maxDistance:
            bizID = business["id"]
            bizName = business["name"]
            bizLat = business["coordinates"]["latitude"]
            bizLng = business["coordinates"]["longitude"]
            bizDistance = business["distance"]
            bizURL = business["url"]
            d[bizID] = {'name': bizName, 'lat': bizLat, 'lng': bizLng, 'distance': bizDistance, 'url': bizURL}


# TODO: Uncomment the line below and add your Yelp API key.
# HEADERS={"Authorization":"Bearer YOUR_KEY_HERE"}
def getBusinessesInfo(searchTerm, lat, lng, radius):
    '''
    Finds all nearby businesses around a given location on a map via the Yelp API.
    We are using Yelp because it can return up to 1000 unique businesses rather than 60 from Google.
    It seems pretty feasible that a person can walk to >60 unique restaurants within a half hour in a city.
    
    Example Call:
        getBusinessesInfo("delis", 37.786882, -122.399972, 1000)

    Args:
        searchTerm (a string): what kind of business the user is searching for
        lat (a float): the latitude of where the user is
        lng (a float): the longitude of where the user is
        radius (an int): the search radius in meters - how far a person is willing to walk from their location


    Returns:
        A dictionary where each key is the unique id string of a business and the value is a dictionary with the following:
            - name (string): name of the business
            - lat (float): latitude location of the business
            - lng (float): longitude location of the business
            - distance (float): how far the distance is from the query latitude and longitude in meters
    '''
    limit = 50
    url = "https://api.yelp.com/v3/businesses/search?" + \
          "term=" + searchTerm + \
          "&limit=" + str(limit) + \
          "&radius=" + str(radius) + \
          "&latitude=" + str(lat) + \
          "&longitude=" + str(lng)
    print url
    offset = 0
    d = {}

    total = 1
    while offset < total:
        r = requests.get(url + "&offset=" + str(offset), headers=HEADERS)
        json = byteify(r.json())
        while "total" not in json:
            # exceeded yelp's limit rate
            time.sleep(1)
            r = requests.get(url + "&offset=" + str(offset), headers=HEADERS)
            json = byteify(r.json())
            print "waiting"
            print json

        total = json["total"]
        businesses = json["businesses"]
        addBusinessesToDict(businesses, radius, d)
        print "fetched from", offset, "entry, got", len(businesses), "entries out of", total

        offset += limit

    return d

def getAllBusinessesInfo(searchTerm, searchDimensions, foundData):
    '''
    Finds all nearby businesses around a list of given locations on a map via the Yelp API.

    Args:
        searchTerm (a string): what kind of business the user is searching for
        searchDimensions (a list of dictionaries): contains all search areas, where each entry has info
            about the radius to search around each lat-long pair
    '''
    excludedData = { key: val for d in foundData for key, val in d.items() }

    data = {}
    for d in searchDimensions:
        businesses = getBusinessesInfo(searchTerm, float(d["lat"]), float(d["lng"]), int(d["radius"]))
        for businessId, businessInfo in businesses.iteritems():
            if businessId not in excludedData:
                if businessId in data:
                    data[businessId]['distance'] = min(data[businessId]['distance'], businessInfo['distance'])
                else:
                    data[businessId] = businessInfo

    print data
    return data
