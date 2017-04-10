import sys, json, copy
import http.client
import urllib.parse
import shapely.wkt

BEACON_HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'OA',
    }

BODY_TEMPLATE = {
    "layerId": None,
    "useSelection": False,
    "ext": {
        "minx": 0,
        "miny": 0,
        "maxx": 40000000,
        "maxy": 40000000
        },
    "wkt": None,
    "spatialRelation": 1,
    "featureLimit": 1
    }

def get_connection(raw_url):
    ''' Return an HTTPConnection and URL path for a starting Beacon URL.
    
        Expects a raw URL similar to:
        https://beacon.schneidercorp.com/api/beaconCore/GetVectorLayer?QPS=xxxx
    '''
    # Safari developer tools sneaks in some zero-width spaces:
    # http://www.fileformat.info/info/unicode/char/200B/index.htm
    url = raw_url.replace('\u200b', '')

    scheme, host, path, _, query, _ = urllib.parse.urlparse(url)
    layer_path = urllib.parse.urlunparse(('', '', path, None, query, None))
    
    if scheme == 'https':
        return http.client.HTTPSConnection(host), layer_path
    elif scheme == 'http':
        return http.client.HTTPConnection(host), layer_path

def get_starting_bbox(conn, layer_path, layer_id, radius_km=200):
    ''' Retrieves a bounding box tuple for a Beacon layer and radius in km.
    
        This is meant to be an overly-large, generous bbox that should
        encompass any reasonable county or city data source.
    '''
    body = copy.deepcopy(BODY_TEMPLATE)
    body['layerId'] = int(layer_id)
    
    conn.request(
        'POST', url=layer_path,
        body=json.dumps(body),
        headers=BEACON_HEADERS
        )
    
    resp = conn.getresponse()
    
    if resp.status not in range(200, 299):
        raise RuntimeError('Bad status in get_starting_bbox')
    
    results = json.load(resp)
    wkt = results.get('d', [{}])[0].get('WktGeometry', None)

    if not wkt:
        raise RuntimeError('Missing WktGeometry in get_starting_bbox')
    
    xmin, ymin, xmax, ymax = shapely.wkt.loads(wkt).buffer(radius_km*1000).bounds

    return xmin, ymin, xmax, ymax

def recursively_descend(conn, layer_path, layer_id, bbox, limit=None):
    '''
    '''
    body = copy.deepcopy(BODY_TEMPLATE)
    body['layerId'], body['featureLimit'] = int(layer_id), 0
    body['ext'] = dict(minx=bbox[0], miny=bbox[1], maxx=bbox[2], maxy=bbox[3])
    
    conn.request(
        'POST', url=layer_path,
        body=json.dumps(body),
        headers=BEACON_HEADERS
        )
    
    resp = conn.getresponse()
    
    if resp.status not in range(200, 299):
        raise RuntimeError('Bad status in recursively_descend')

    results = json.load(resp)
    return results.get('d', [])

if __name__ == '__main__':
    _, raw_url, layer_id = sys.argv
    
    conn, layer_path = get_connection(raw_url)
    bbox = get_starting_bbox(conn, layer_path, layer_id)
    print(bbox)
    
    recursively_descend(conn, layer_path, layer_id, bbox)
