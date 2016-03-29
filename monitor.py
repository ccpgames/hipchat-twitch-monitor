from twitch.api import v3 as twitch
import sched, time
from hypchat import HypChat
import os

activeStreams = {}
streamMonitor = sched.scheduler(time.time, time.sleep)
streamMonitorEvent = ""
token = os.environ.get("TWITCH_HIPCHAT_TOKEN_V2")
hipChat = HypChat(token, os.environ.get("TWITCH_HIPCHAT_BASE_URI"))
twitchRoom = hipChat.get_room(os.environ.get("TWITCH_HIPCHAT_ROOM"))
gamesList = str(os.environ.get("TWTICH_GAMES")).split(";")

def main():

    monitorRun = True

    twitchRoom.notification("Twitch Monitor has started", "green", "False", "text")
    for game in gamesList:
        updateActiveStreams(game, True)
    while monitorRun:
        streamMonitor.run()
    streamMonitor.empty()
    twitchRoom.notification("Twitch Monitor has stopped", "red", "False", "text")


def updateActiveStreams(gameName, suppressNotifcation=False):
    #Dict for updated streams. Key is stream ID, value is True if they've gone active, False if they've gone inactive - will replace with an enum later
    updatededStreamList = {}

    streamList = twitch.streams.all(gameName)["streams"]

    #First check to see if there are new streams
    for stream in streamList:
        if stream["channel"]["_id"] not in activeStreams and stream["channel"]["game"] == gameName: #need to do some sanity checking as we've had a few other games sneak in before
            #suppress for first run so we don't spam the channel
            if not suppressNotifcation:
                twitchRoom.notification("<a href=\"%s\">%s has started streaming %s</a>" %
                                        (stream["channel"]["url"], stream["channel"]["display_name"], stream["channel"]["game"]),
                                        "purple", "True", "html")
            updatededStreamList[stream["channel"]["_id"]] = True
            newStream = StreamDetails(stream["channel"]["_id"],
                                      stream["channel"]["display_name"],
                                      stream["channel"]["status"],
                                      stream["channel"]["url"],
                                      stream["channel"]["game"],
                                      stream["channel"]["partner"])
            activeStreams[stream["channel"]["_id"]] = newStream

    #Now we look for whether any streams have gone offline
    #Pull the stream IDs into a list to make it easier
    ActiveStreamIdList = []
    for stream in streamList:
        ActiveStreamIdList.append(stream["channel"]["_id"])

    #need to hold the now inactive IDs in a list and removed them after iterating through the dictionary
    inactiveStreams = []

    for stream in activeStreams:
        #if a stream is active, reset it's last active time and set it to active
        if stream in ActiveStreamIdList:
            activeStreams[stream].resetLastActive()
            activeStreams[stream].setActivityState(True)
        #remove a stream from the list of streams if we haven't seen it for more than 600 seconds
        elif (time.time() - activeStreams[stream].getLastActive()) > 600:
            inactiveStreams.append(stream)
        #class a stream as inactive if we haven't seen it for more than 120 seconds but less than 600
        elif (time.time() - activeStreams[stream].getLastActive()) > 120:
            activeStreams[stream].setActivityState(False)
            updatededStreamList.update({stream: False})

    #Now we can remove inactive streams from the list
    for stream in inactiveStreams:
        activeStreams.pop(stream)

    if len(updatededStreamList) > 0:
        numActiveStreams = 0
        for stream in activeStreams:
            if activeStreams[stream].isActive: numActiveStreams += 1
    streamMonitorEvent = streamMonitor.enter(15, 2, updateActiveStreams, (gameName,))
    return updatededStreamList

def getStreamDetails(streamId):
    streamId = int(streamId)
    stream = activeStreams.get(streamId)
    return [stream.streamId, stream.streamerName, stream.streamName, stream.streamURL, stream.isPartner]

class StreamDetails:

    def __init__(self, streamId, streamerName, streamName, streamURL, streamGame, isPartner=False):
        self.streamId = streamId
        self.streamerName = streamerName
        self.streamName = streamName
        self.streamURL = streamURL
        self.streamGame = streamGame
        self.isPartner = isPartner
        self.isActive = True
        self.lastActive = time.time()

    def resetLastActive(self):
        self.lastActive = time.time()

    def setActivityState(self, isActive):
        self.isActive = isActive

    def getLastActive(self):
        return self.lastActive

if __name__ == '__main__': main()