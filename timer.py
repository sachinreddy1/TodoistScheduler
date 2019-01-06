from datetime import datetime
from pytz import timezone
from dateutil import tz
import math

BLOCK_LEN = 2
MIN_IN_HR = 60

class Timer(object):
    def __init__(self):
        self.elapsed_time = []
        self.elapsed_pause = []

    def start(self):
        self.start = datetime.now()
        return
    
    def stop(self):
        self.stop = datetime.now()
        t1 = self.start
        t2 = self.stop
        self.elapsed_time.append(t2 - t1)
        return self.blocksConverter(self.start, self.stop)
    
    def split(self):
        self.split_start = datetime.now()
        self.elapsed_time.append(self.split_start - self.start)
        message = "Pause at: " + str(self.split_start).split(' ')[1]
        blocks = self.blocksConverter(self.start, self.split_start)
        return message, blocks
    
    def unsplit(self):
        t1 = self.split_start
        t2 = datetime.now()
        self.start = t2
        self.elapsed_pause.append(t2 - t1)
        return self.blocksConverter(t1, t2)
    
    def elapsed(self):
        t1 = self.start
        t2 = datetime.now()
        return str(t2 - t1), self.blocksConverter(t1, t2)
    
    def elapsedPause(self):
        t1 = self.split_start
        t2 = datetime.now()
        return str(t2 - t1), self.blocksConverter(t1, t2)
    
    def blocksConverter(self, time1, time2):
        strval = str(time2-time1).split(":")
        hrs = int(strval[0])
        mins = int(strval[1])
        return int(hrs*(MIN_IN_HR/BLOCK_LEN)) + int(mins/BLOCK_LEN)
