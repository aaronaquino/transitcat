from isochrone_utils import full_isochrone_transitland
import pprint as pp
from datetime import timedelta


thaiphoon_coord = (37.444270, -122.161809)
caltrain_feed_id = "f-9q9-caltrain"
reachable = full_isochrone_transitland(caltrain_feed_id, thaiphoon_coord, 3, 12, 0, timedelta(minutes=30))

pp.pprint(reachable)