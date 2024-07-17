# Authors: Sergio Cárdenas & Adrián Cerezuela

import collections
import networkx as nx
import osmnx as ox
import pickle
import urllib.request
import csv
from staticmap import StaticMap, Line, CircleMarker


Highway = collections.namedtuple('Highway', ['way_id', 'description',
                                 'coordinates'])
Congestion = collections.namedtuple('Congestion', ['way_id', 'date', 'state'])


def exists_graph(GRAPH_FILENAME):
    """Returns True if the graph already exists.
    --------------------------------------------
    Keyword arguments:
    GRAPH_FILENAME -- Name of the graph we are looking for.
    """

    try:
        with open(GRAPH_FILENAME) as file:
            return True
    except:
        return False


def get_digraph(graph):
    """Turns an undirected graph into a directed graph.
    ---------------------------------------------------
    Keyword arguments:
    graph -- The graph we want to convert.
    """

    graph = ox.utils_graph.get_digraph(graph, weight='length')
    return graph


def download_graph(PLACE):
    """Downloads a graph from a given place.
    ----------------------------------------
    Keyword arguments:
    PLACE -- Name of the place we want to download the graph from.
    """

    graph = ox.graph_from_place(PLACE, network_type='drive', simplify=True)
    return graph


def save_graph(graph, GRAPH_FILENAME):
    """Saves a graph in a determined file.
    --------------------------------------
    Keyword arguments:
    graph -- Name of the graph we want to save.
    GRAPH_FILENAME -- Name that we give to the file where we save the graph.
    """

    with open(GRAPH_FILENAME, 'wb') as file:
        pickle.dump(graph, file)


def load_graph(GRAPH_FILENAME):
    """Loads a graph from a determined file.
    ---------------------------------------
    Keyword arguments:
    GRAPH_FILENAME -- Name of the file we are loading the graph from.
    """

    with open(GRAPH_FILENAME, 'rb') as file:
        graph = pickle.load(file)
    return graph


def plot_graph(graph):
    """Plots a certain graph we give as a parameter and saves it as a png file.
    ---------------------------------------------------------------------------
    Keyword arguments:
    graph -- Name of the graph we want to plot.
    """

    ox.plot_graph(graph, show=False, save=True, filepath='barcelona.png')


def fix_coordinates(coordinates):
    """Returns a list of fixed format coordinates.
    ----------------------------------------------
    Keyword arguments:
    coordinates -- List of coordinates representing points on a highway.
    """

    # separates each coordinate string
    coordinates = coordinates.split(',')
    # converts each coordinate string into a float
    coordinates = [float(coordinate) for coordinate in coordinates]
    # groups every pair of coordinates (longitude and latitude)
    coordinates_pairs = list(zip(*[iter(coordinates)] * 2))
    return coordinates_pairs


def download_highways(HIGHWAYS_URL):
    """Downloads highways data from a URL.
    --------------------------------------
    Keyword arguments:
    HIGHWAYS_URL -- The URL where we want to download the highways data from.
    """

    with urllib.request.urlopen(HIGHWAYS_URL) as response:
        lines = [l.decode('utf-8') for l in response.readlines()]
        reader = csv.reader(lines, delimiter=',', quotechar='"')
        next(reader)  # ignore first line with description
        highways = []
        for line in reader:
            way_id, description, coordinates = line
            coordinates = fix_coordinates(coordinates)
            highways.append(Highway(way_id, description, coordinates))
    return highways


def plot_highways(highways, png, SIZE):
    """Plots the highways we give as an argument and saves them as a png file.
    --------------------------------------------------------------------------
    Keyword arguments:
    highways -- List of highways we want to plot.
    png -- File where we want to save the in PNG format.
    SIZE -- Size of the map where we want to plot the highways to.
    """

    map = StaticMap(SIZE, SIZE)
    for highway in highways:
        line = Line(highway.coordinates, 'red', 3)
        map.add_line(line)
    image = map.render()
    image.save(png)


def download_congestions(CONGESTIONS_URL):
    """Downloads congestions data from a URL.
    -----------------------------------------
    Keyword arguments:
    CONGESTIONS_URL -- The URL where we want to download the congestions data
    from.
    """

    with urllib.request.urlopen(CONGESTIONS_URL) as response:
        lines = [l.decode('utf-8') for l in response.readlines()]
        reader = csv.reader(lines, delimiter='#', quotechar='"')
        congestions = []
        for line in reader:
            way_id, date, actual_state, planned_state = line
            congestions.append(Congestion(way_id, date, actual_state))
    return congestions


def congestion_state(state):
    """Provides the line colour in function of the congestion level of the
    highway.
    ----------------------------------------------------------------------
    Keyword arguments:
    state -- Actual congestion of a certain highway.
    """

    if (state == '0'):  # without data
        return 'gray'
    if (state == '1'):  # very fluid
        return 'cornflowerblue'
    if (state == '2'):  # fluid
        return 'limegreen'
    if (state == '3'):  # dense
        return 'khaki'
    if (state == '4'):  # very dense
        return 'orangered'
    if (state == '5'):  # congestion
        return 'red'
    if (state == '6'):  # cut
        return 'black'
    return None


def plot_congestions(highways, congestions, png, SIZE):
    """Plots the congestion of every highway in the graph in a certain day and
    hour, and saves the result as a png file.
    --------------------------------------------------------------------------
    Keyword arguments:
    highways -- List of highways we want to plot.
    congestions -- List of congestions we want to plot.
    png -- File where we want to save the in PNG format.
    SIZE -- Size of the map where we want to plot the congestions.
    """

    map = StaticMap(SIZE, SIZE)
    for highway in highways:
        id = int(highway.way_id)
        try:
            colour = congestion_state(congestions[id].state)
            line = Line(highway.coordinates, colour, 3)
            map.add_line(line)
        except:
            None
    image = map.render()
    image.save(png)


def congestion(state):
    """Returns the congestion value that will be applied to a street speed.
    -----------------------------------------------------------------------
    Keyword arguents:
    state -- Actual congestion of a certain highway.
    """

    if (state == '1'):
        congestion = 1
    elif (state == '2' or state == '0'):
        congestion = 0.8
    elif (state == '3'):
        congestion = 0.6
    elif (state == '4'):
        congestion = 0.4
    elif (state == '5'):
        congestion = 0.2
    elif (state == '6'):
        congestion = 0
    return congestion


def build_igraph(graph, highways, congestions):
    """Returns a directed graph, from an undirected one, with intelligent
    attributes.
    ---------------------------------------------------------------------
    Keyword arguments:
    graph -- Undirected graph based on which we will construct the
             intelligent graph.
    highways -- List that contains the highways data for a certain place.
    congestions -- List that contains the congestion data for every highway.
    """

    igraph = get_digraph(graph)
    nx.set_edge_attributes(igraph, None, 'itime')

    for highway in highways:
        x_coordinate, y_coordinate = highway.coordinates[0]
        node1 = ox.nearest_nodes(igraph, x_coordinate, y_coordinate)
        for x_coordinate, y_coordinate in highway.coordinates[1:]:
            node2 = ox.nearest_nodes(igraph, x_coordinate, y_coordinate)

            # some highways are from outside of Barcelona
            try:
                shortest_path = ox.shortest_path(igraph, node1, node2)
                point1 = shortest_path[0]
                for point2 in shortest_path[1:]:
                    edge = igraph[point1][point2]
                    length = float(edge['length'])
                    try:
                        speed = float(edge['maxspeed'])
                    except:
                        # we set 20 km/h as standard speed if no speed is given
                        speed = 20
                    try:
                        id = int(highway.way_id)
                        state = congestions[id].state
                    except:
                        state = '0'  # no data
                    congestion = congestion(state)
                    edge['itime'] = length/(speed*congestion)
                    point1 = point2
            except:
                None

            node1 = node2

    for node1, info in igraph.nodes.items():
        for node2, edge in igraph.adj[node1].items():
            if (edge['itime'] is None):
                length = float(edge['length'])
                try:
                    speed = float(edge['maxspeed'])
                except:
                    speed = 20
                edge['itime'] = length/(speed*0.8)

    return igraph


def get_node(graph, location):
    """Returns the nearest node in the given graph from a certain location.
    ----------------------------------------------------------------------
    Keyword arguments:
    graph -- Graph where we want to find the node.
    location -- Name of the location from which we are looking for
                the nearest node.
    """

    complete_location = location + ", Barcelona, Catalunya"
    coordinates = ox.geocode(complete_location)
    node = ox.nearest_nodes(graph, coordinates[1], coordinates[0])
    return node


def get_shortest_path_with_ispeeds(graph, source, target):
    """Returns a list of nodes that represents the shortest path between two
    locations, applying the itime attribute.
    -----------------------------------------------------------------------
    Keyword arguments:
    graph -- Graph where is represented a determined place.
    source -- Location from which we want to start the path.
    target -- Location that we want to reach.
    """

    source_node = get_node(graph, source)
    target_node = get_node(graph, target)
    path = ox.shortest_path(graph, source_node, target_node, 'itime')
    return path


def plot_path(graph, path, SIZE):
    """Plots the shortest path, previously found, between two locations and
    saves the result as a png file.
    -----------------------------------------------------------------------
    Keyword arguments:
    graph -- Graph where is represented a determined place.
    path -- List of nodes that constitute the shortest path between
            two locations.
    SIZE -- Size of the map where we want to plot the path to.
    """

    # plots the path
    coordinates = []
    for point in path:
        for node1, info in graph.nodes.items():
            if (node1 == point):
                coordinates.append([info['x'], info['y']])
    map = StaticMap(SIZE, SIZE)
    line = Line(coordinates, 'red', 3)
    map.add_line(line)

    # plots source and target points
    coordinates = [coordinates[0], coordinates[len(coordinates)-1]]
    for coordinate in coordinates:
        marker_outline = CircleMarker(coordinate, 'darkred', 8)
        marker = CircleMarker(coordinate, 'red', 5)
        map.add_marker(marker_outline)
        map.add_marker(marker)

    image = map.render()
    image.save('shortestpath.png')


# 'if __name__ == "__function__"' allows us to run a function of the module
# igo when it is imported

if __name__ == "__exists_graph__":
    main(sys.argv[1])

if __name__ == "__get_digraph__":
    main(sys.argv[1])

if __name__ == "__download_graph__":
    main(sys.argv[1])

if __name__ == "__save_graph__":
    main(sys.argv[1], sys.argv[2])

if __name__ == "__load_graph__":
    main(sys.argv[1])

if __name__ == "__plot_graph__":
    main(sys.argv[1])

if __name__ == "__fix_coordinates__":
    main(sys.argv[1])

if __name__ == "__download_highways__":
    main(sys.argv[1])

if __name__ == "__plot_highways__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])

if __name__ == "__download_congestions__":
    main(sys.argv[1])

if __name__ == "__congestion_state__":
    main(sys.argv[1])

if __name__ == "__plot_congestions__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

if __name__ == "__congestion__":
    main(sys.argv[1])

if __name__ == "__build_igraph__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])

if __name__ == "__get_node__":
    main(sys.argv[1], sys.argv[2])

if __name__ == "__get_shortest_path_with_ispeeds__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])

if __name__ == "__plot_path__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
