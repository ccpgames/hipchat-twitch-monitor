import os
import sched
import time
import logging
import sys
import socket

from twitch.api import v3 as twitch
from hypchat import HypChat
from twitch.exceptions import ResourceUnavailableException

token = os.environ.get("TWITCH_HIPCHAT_TOKEN_V2", "")
twitch_games = os.environ.get("TWITCH_GAMES", "").split(";")
hipchat_uri = os.environ.get("TWITCH_HIPCHAT_BASE_URI", "")
hipchat_room = os.environ.get("TWITCH_HIPCHAT_ROOM", "")

if "" in [token, twitch_games, hipchat_uri, hipchat_room]:
    if token == "":
        logging.error("The Environment variable TWITCH_HIPCHAT_TOKEN_V2 is missing")
    if twitch_games == [""]:
        logging.error("The Environment variable TWITCH_GAMES is missing")
    if hipchat_uri == "":
        logging.error("The Environment variable TWITCH_HIPCHAT_BASE_URI is missing")
    if hipchat_room == "":
        logging.error("The Environment variable TWITCH_HIPCHAT_ROOM is missing")
    sys.exit(1)

hipchat_connection = HypChat(token, hipchat_uri)
twitch_room = hipchat_connection.get_room(hipchat_room)
stream_monitor = sched.scheduler(time.time, time.sleep)
logging.basicConfig(level=logging.INFO)

active_streams = {}


def main():
    twitch_room.notification("Twitch Monitor has started on {}".format(socket.gethostname()), "green", "False", "text")
    logging.info("Twitch Monitor has started on {}".format(socket.gethostname()))

    try:
        for game in twitch_games:
            # suppress notifications for first run so we don't spam the channel
            update_active_streams(game, True)
        while True:
            stream_monitor.run()
        stream_monitor.empty()

    finally:
        twitch_room.notification("Twitch Monitor has stopped on {}".format(socket.gethostname()),
                                 "red", "False", "text")
        logging.info("Twitch Monitor has stopped on {}".format(socket.gethostname()))


def update_active_streams(game_name, suppress_notification=False):
    # Dict for updated streams. Key is stream ID, value is True if they've gone active,
    # False if they've gone inactive - will replace with an enum later
    updated_stream_list = {}

    try:
        stream_list = twitch.streams.all(game_name)["streams"]
    except ResourceUnavailableException as e:
        logging.warning("Failed to get list of active streams for {}".format(game_name))
        stream_monitor.enter(15, 2, update_active_streams, (game_name,))
        return updated_stream_list

    # First check to see if there are new streams
    for stream in stream_list:
        # need to do some sanity checking as we've had a few other games sneak in before
        if stream["channel"]["_id"] not in active_streams and stream["channel"]["game"] == game_name:
            if not suppress_notification:
                twitch_room.notification(
                    "<a href=\"{}\">{} has started streaming {}</a>".format(
                        stream["channel"]["url"],
                        stream["channel"]["display_name"],
                        stream["channel"]["game"]
                    ),
                    "purple", "True", "html"
                )
            logging.info("{} has started streaming {}".format(
                stream["channel"]["display_name"],
                stream["channel"]["game"]
            ))

            updated_stream_list[stream["channel"]["_id"]] = True

            new_stream = StreamDetails(
                stream["channel"]["_id"],
                stream["channel"]["display_name"],
                stream["channel"]["status"],
                stream["channel"]["url"],
                stream["channel"]["game"],
                stream["channel"]["partner"]
            )
            active_streams[stream["channel"]["_id"]] = new_stream

    # Now we look for whether any streams have gone offline
    # Pull the stream IDs into a list to make it easier
    active_stream_id_list = [stream["channel"]["_id"] for stream in stream_list]

    # need to hold the now inactive IDs in a list and removed them after iterating through the dictionary
    inactive_streams = []

    for stream in active_streams:
        # if a stream is active, reset it's last active time and set it to active
        if stream in active_stream_id_list:
            active_streams[stream].reset_last_active()
            active_streams[stream].set_activity_state(True)
        # remove a stream from the list of streams if we haven't seen it for more than 600 seconds
        elif (time.time() - active_streams[stream].get_last_active()) > 600:
            inactive_streams.append(stream)
            logging.info("{} has stopped streaming {}".format(
                active_streams[stream].streamer_name,
                active_streams[stream].stream_game
            ))
        # class a stream as inactive if we haven't seen it for more than 120 seconds but less than 600
        elif (time.time() - active_streams[stream].get_last_active()) > 120:
            active_streams[stream].set_activity_state(False)
            updated_stream_list.update({stream: False})

    # Now we can remove inactive streams from the dict
    for stream in inactive_streams:
        active_streams.pop(stream)

    stream_monitor.enter(15, 2, update_active_streams, (game_name,))
    return updated_stream_list


class StreamDetails:
    def __init__(self, stream_id, streamer_name, stream_name, stream_url, stream_game, is_partner=False):
        self.stream_id = stream_id
        self.streamer_name = streamer_name
        self.stream_name = stream_name
        self.stream_url = stream_url
        self.stream_game = stream_game
        self.is_partner = is_partner

        self.is_active = True
        self.last_active = time.time()

    def reset_last_active(self):
        self.last_active = time.time()

    def set_activity_state(self, is_active):
        self.is_active = is_active

    def get_last_active(self):
        return self.last_active

if __name__ == '__main__':
    main()
