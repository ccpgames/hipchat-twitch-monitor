from twitch.api import v3 as twitch
import sched, time
from hypchat import HypChat

activeStreams = {}
streamMonitor = sched.scheduler(time.time, time.sleep)
streamMonitorEvent = ""
token = "NDa4Og8jYHqQV9JzBb1RlCLBfSaGcaHFRkZfkR3s"
hipChat = HypChat(token, endpoint="https://hipchat.ccpgames.com")
twitchRoom = hipChat.get_room("CCP Twitch")

def main():

    updateActiveStreams("EVE: Valkyrie", True)
    updateActiveStreams("EVE Online", True)
    while True:
        streamMonitor.run()
    streamMonitor.empty()


def updateActiveStreams(gameName, suppressNotifcation=False):
    #Dict for updated streams. Key is stream ID, value is True if they've gone active, False if they've gone inactive - will replace with an enum later
    updatededStreamList = {}

    streamList = twitch.streams.all(gameName)["streams"]

    #First check to see if there are new streams
    for stream in streamList:
        if stream["channel"]["_id"] not in activeStreams and stream["channel"]["game"] == gameName: #need to do some sanity checking as we've had a few other games sneak in before
            #suppress for first run so we don't spam the channel
            if not suppressNotifcation:
                twitchRoom.notification("<a href=\"%s\">%s has started streaming %s</a>" % (stream["channel"]["url"], stream["channel"]["display_name"], stream["channel"]["game"]), "purple", "True", "html")
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
            activeStreams[stream].setActive(True)
        #remove a stream from the list of streams if we haven't seen it for more than 600 seconds
        elif (time.time() - activeStreams[stream].getLastActive()) > 600:
            inactiveStreams.append(stream)
        #class a stream as inactive if we haven't seen it for more than 120 seconds but less than 600
        elif (time.time() - activeStreams[stream].getLastActive()) > 120:
            activeStreams[stream].setActive(False)
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
        self.streamId, self.streamerName, self.streamName, self.streamURL, self.streamGame, self.isPartner = streamId, streamerName, streamName, streamURL, streamGame, isPartner
        self.isActive = True
        self.lastActive = time.time()

    def resetLastActive(self):
        self.lastActive = time.time()

    def setActive(self, isActive):
        self.isActive = isActive

    def getLastActive(self):
        return self.lastActive

if __name__ == '__main__': main()