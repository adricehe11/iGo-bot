# Authors: Sergio Cárdenas & Adrián Cerezuela

import igo
import random
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from staticmap import StaticMap, CircleMarker
from datetime import datetime, timedelta


PLACE = 'Barcelona, Catalonia'
GRAPH_FILENAME = 'barcelona.graph'
SIZE = 800
HIGHWAYS_URL = 'https://opendata-ajuntament.barcelona.cat/data/dataset/1090983a-1c40-4609-8620-14ad49aae3ab/resource/1d6c814c-70ef-4147-aa16-a49ddb952f72/download/transit_relacio_trams.csv'
CONGESTIONS_URL = 'https://opendata-ajuntament.barcelona.cat/data/dataset/8319c2b1-4c21-4962-9acd-6db4c5ff1148/resource/2d456eb5-4ea6-4f68-9794-2f3f1a58a933/download'


def startup():
    """Starts-up our bot by downloading all the necessary resources.
    """

    # we will use the following global variables
    global graph, igraph, highways, congestions, last_download
    # load/download graph (using cache)
    if not igo.exists_graph(GRAPH_FILENAME):
        graph = igo.download_graph(PLACE)
        igo.save_graph(graph, GRAPH_FILENAME)
    else:
        graph = igo.load_graph(GRAPH_FILENAME)
    highways = igo.download_highways(HIGHWAYS_URL)
    congestions = igo.download_congestions(CONGESTIONS_URL)
    last_download = datetime.now()
    igraph = igo.build_igraph(graph, highways, congestions)
    # we declare the users_information variable as a list, where we will store
    # the current position and ID of the different users
    global users_information
    users_information = []

startup()


def start(update, context):
    """Starts a conversation and will be executed when the bot receives the
    message '/start'.
    """

    name = update.effective_chat.first_name
    message = "Hi, %s! I am a bot of the module iGo." % (name)
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)


def help(update, context):
    """Offers the available commands and will be executed when the bot receives
    the message '/help'.
    """

    message = "These are my commands:\n /start: starts a conversation.\n /help: shows the available commands.\n /author: shows the names of the authors of the project.\n /go <target>: shows a map to go from the current location to the target location by the shortest path using the itime concept.\n /where: shows the user's current location."
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=message)


def author(update, context):
    """Shows the name of the authors of the project and will be executed
    when the bot receives the message '/author'.
    """

    message = "I am a bot created by Sergio Cárdenas & Adrián Cerezuela, Data & Science Engineering students from UPC."
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=message)


def source_pos(chat_id):
    """Given the current chat ID, searches in the users_information list the
    user with the same ID and returns its position.
    """

    for user_position, user_id in users_information:
        if (user_id == chat_id):
            return user_position


def update_igraph(update, context):
    """Update the igraph if it was last updated more than 5 minutes ago.
    """

    global igraph, last_download
    current_datetime = datetime.now()
    elapsed_time = current_datetime - last_download
    seconds_passed = elapsed_time.total_seconds()
    if (seconds_passed > 300):
        last_download = current_datetime
        igraph = igo.build_igraph(graph, highways, congestions)


def go(update, context):
    """Shows the user a map to get from its current position to the target
    point by the shortest path according to the itime concept and which
    will be executed when the bot receives the message '/go'.
    """

    # checks if it is necessary to update the igraph
    update_igraph(update, context)
    try:
        # if there is no arguments on the 0 position it means that target
        # location has not been read, so it will raise an exception
        context.args[0]
        # we save the target and source locations as string-type variables
        target = ' '.join(context.args)
        source = source_pos(update.effective_chat.id)
        # we find the shortest path to go from the source to the target and
        # plot it using the get_shortest_path_with_ispeeds and plot_path
        # functions from the igo module
        ipath = igo.get_shortest_path_with_ispeeds(igraph, source, target)
        igo.plot_path(igraph, ipath, SIZE)
        context.bot.send_photo(chat_id=update.effective_chat.id,
                               photo=open('shortestpath.png', 'rb'))
    except Exception as e:
        print(e)
        context.bot.send_message(chat_id=update.effective_chat.id, text='💣')


def save_current_location(current_location, chat_id):
    """Saves the current user's position and its ID in a list.
    """

    global users_information
    user_already_exists = False  # checks if the user already exists
    list_position = 0
    for user_position, user_id in users_information:
        # if the ID of the current user matches any ID in the list, we will
        # replace its saved location in the list with the current one
        if (user_id == chat_id):
            users_information[list_position][0] = current_location
            user_already_exists = True
        ++list_position
    if (not user_already_exists):
        # if the user does not exist, we will add its information to the list
        users_information.append([current_location, chat_id])


def where(update, context):
    """Shows the current user's position and will be executed when the
    bot receives the message '/where'.
    """

    try:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        current_location = lat, lon
        # we save the location of the user in the users_information list
        save_current_location(current_location, update.effective_chat.id)
        # we will show the user its location in a map of given size
        file = "%d.png" % random.randint(1000000, 9999999)
        map = StaticMap(SIZE, SIZE)
        map.add_marker(CircleMarker((lon, lat), 'blue', 10))
        image = map.render()
        image.save(file)
        context.bot.send_photo(chat_id=update.effective_chat.id,
                               photo=open(file, 'rb'))
        os.remove(file)
    except Exception as e:
        print(e)
        context.bot.send_message(chat_id=update.effective_chat.id, text='💣')


def pos(update, context):
    """Sets a current position of the user and will be executed when the bot
    receives the message '/pos'.
    """

    try:
        # if there is no arguments on the 0 position it means that current
        # location has not been read, so it will raise an exception
        context.args[0]
        # we save the current user location as string-type variables
        current_location = ' '.join(context.args)
        # we save the position of the user in the users_information list
        save_current_location(current_location, update.effective_chat.id)
    except Exception as e:
        print(e)
        context.bot.send_message(chat_id=update.effective_chat.id, text='💣')


# declares a constant with the token access that reads from token.txt
TOKEN = open('token.txt').read().strip()

# creates objects to work with Telegram
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# when the bot receives a certain command, its associated function will be
# executed
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', help))
dispatcher.add_handler(CommandHandler('author', author))
dispatcher.add_handler(CommandHandler('go', go))
dispatcher.add_handler(CommandHandler('pos', pos))
dispatcher.add_handler(MessageHandler(Filters.location, where))

# turns on the bot
updater.start_polling()
