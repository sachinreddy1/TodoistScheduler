from datetime import datetime
from pytz import timezone
from dateutil import tz
import math

BLOCK_LEN = 1

class Timer(object):
    def __init__(self):
        pass
    
    def start(self, message="Started at: "):
        self.start = datetime.now()
        msg = str(self.start).split(' ')[1]
        return message + msg
    
    def stop(self, message="Total: "):
        self.stop = datetime.now()
        return self.blocksConverter(self.start, self.stop)
    
    def now(self, message="Now: "):
        return message + ": " + str(datetime.now())
    
    def elapsed(self, message="Elapsed: "):
        t1 = self.start
        t2 = datetime.now()
        return str(t2 - t1), self.blocksConverter(t1, t2)
    
    def split(self, message="Pause at: "):
        self.split_start = datetime.now()
        return message + str(self.split_start).split(' ')[1]
    
    def getblocks(self):
        return self.blocksConverter(self.start, datetime.now())
    
    def unsplit(self, message="Elapsed pause: "):
        msg = str(datetime.now() - self.split_start)
        return self.blocksConverter(self.split_start, datetime.now())
    
    def elapsedPause(self, message="Elapsed: "):
        t1 = self.split_start
        t2 = datetime.now()
        b = self.blocksConverter(t1, t2)
        if b < 0:
            print(t1.minute, t2.minute)
        return str(t2 - t1), b
    
    def unsplitblocks(self):
        return self.blocksConverter(self.split_start, datetime.now())
    
    def blocksConverter(self, time1, time2):
        d = time2.minute - time1.minute
        blocks = math.floor(d / BLOCK_LEN)
        return int(blocks)
