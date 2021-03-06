from datetime import datetime
from pytz import timezone
from dateutil import tz
import math
from globs import *

class Timer(object):
    def __init__(self):
        pass

    def start(self):
        self.start = datetime.now()
        return
    
    def stop(self):
        self.stop = datetime.now()
        t1 = self.start
        t2 = self.stop
        return str(t2-t1), self.blocksConverter(self.start, self.stop)
    
    def split(self):
        self.split_start = datetime.now()
        t1 = self.start
        t2 = self.split_start
        return str(t2-t1), self.blocksConverter(t1, t2)
    
    def unsplit(self):
        t1 = self.split_start
        t2 = datetime.now()
        self.start = t2
        return str(t2-t1), self.blocksConverter(t1, t2)
    
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

