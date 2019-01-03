import todoist
from datetime import datetime
from pytz import timezone
from dateutil import tz
import queue
import threading
import operator
import time
import os
import math
import _pickle as pickle

api = todoist.TodoistAPI()
pickle_path = os.getcwd() + '/misc/persistence.pickle'
USERID = ''
PASSWORD = ''

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
        return str(t2 - t1), self.blocksConverter(t1, t2)

    def unsplitblocks(self):
        return self.blocksConverter(self.split_start, datetime.now())

    def blocksConverter(self, time1, time2):
        d = time2.minute - time1.minute
        blocks = math.floor(d / BLOCK_LEN)
        return int(blocks)

class Application:
    def __init__ (self):
        self.user = USERID
        self.password = PASSWORD
        self.timer = Timer()
        
        self.started = False
        self.paused = False
        
        self.tasks = self.getTasks()
        self.num_tasks = len(self.tasks)
    
        self.total_blocks = 0
        self.leisure_blocks = 0
        
        self.curr_task_num = None
        self.curr_task = None
        self.task_blocks = 0
        self.task_leisure_blocks = 0
    
        self.goal_hrs = 0
        self.goal_blocks = 0

    def get_todays_tasks(self, email, password):
        api.user.login(email, password)
        tasks_today = []
        response = api.sync()
        today = datetime.now(timezone('EST')).strftime("%a %d %b")
        for item in response['items']:
            due = item['due_date_utc']
            if due:
                due_est = self.datetimeConverter(due)
                if due_est == today:
                    tasks_today.append(item)
        return tasks_today
    
    def getTasks(self):
        print("Syncing...")
        v = self.get_todays_tasks(USERID, PASSWORD)
        d = self.task_formatter(v)
        l = sorted(d.items(), key=operator.itemgetter(1), reverse=False)
        print("Done.")
        return l

    def datetimeConverter(self, due):
        from_zone = tz.tzutc()
        to_zone = tz.tzlocal()
        utc = datetime.strptime(due, "%a %d %b %Y %H:%M:%S +0000")
        utc = utc.replace(tzinfo=from_zone)
        utc = utc.replace(tzinfo=from_zone)
        central = utc.astimezone(to_zone).strftime("%a %d %b")
        return central

    def task_formatter(self, items):
        d = {}
        for i in items:
            dv = i['due_date_utc'].split(' ')[4].split(':')
            due_date_val = int(dv[0])*100 + int(dv[1])
            priority_val = i['priority']
            item_val = i['item_order']
            content = i['content']
            id = i['id']
            val = (due_date_val, priority_val, item_val)
            d[(id, content)]=val
        return d

    def printItems(self, items):
        if self.curr_task:
            print("==============  Now:  ==============")
            print("|-> {0}".format(self.curr_task[0][1]))
        print("============  Up Next:  ============")
        for idx, i in enumerate(items):
            id = i[0][0]
            content = i[0][1]
            if i == self.curr_task:
                print("| {0}. {1} <---".format((idx+1), content))
            else:
                print("| {0}. {1}".format((idx+1), content))

    def printStats(self):
        os.system('clear')
        if self.started:
            if self.paused:
                v = self.timer.elapsedPause()
                self.task_leisure_blocks = v[1]
            else:
                v = self.timer.elapsed()
                self.task_blocks = v[1]
        self.printItems(self.tasks)
        print("==========  Statistics:  ===========")
        print("|-> Goal: ")
        print("|  Hours: " + str(self.goal_hrs))
        print("|  Blocks: " + str(self.goal_blocks))
        print("|-> Progress: ")
        print("|  Blocks: " + str(self.total_blocks) + "/" + str(self.goal_blocks))
        print("|  Leisure Blocks: " + str(self.leisure_blocks))
        percent = round( float(self.total_blocks) / float(self.goal_blocks) * 100.0, 2)
        print("|  Percent: " + str(percent) + "%")
        print("|  Tasks: " + str(self.num_tasks - len(self.tasks)) + "/" + str(self.num_tasks))

        if self.started:
            if self.paused:
                print("=============  Break:  =============")
            else:
                print("============  Working:  ============")
            print("|-> {0}".format(self.curr_task[0][1]))
            print("|  Time: " + v[0])
            print("|  Blocks: " + str(v[1]))
        print("====================================")

    def monitor(self):
        helper = '''
            ======  Command List  ======
            - get / g (get tasks from Todoist's server)
            - start [task #]
            - pause / p
            - done / d
            - stats
            - stop
            - exit
            ============================
            '''
        print(helper)
        while True:
            arg = input('-->')
            args = arg.split(' ')
            if arg == '?' or arg == 'help':
                print(helper)
            elif arg == 'get' or arg.startswith('g'):
                self.tasks = self.getTasks()
                self.printItems(self.tasks)
            elif arg.startswith('start'):
                if len(args) != 2:
                    print('[ERROR FORMAT] start task_number')
                    continue
                v = int(args[1])
                if v - 1 >= 0 and v - 1 < len(self.tasks):
                    self.curr_task_num = v
                    self.curr_task = self.tasks[self.curr_task_num-1]
                    self.timer = Timer()
                self.printStats()
                print (self.timer.start())
                print ('Current task: ' + self.curr_task[0][1])
                self.started = True
            elif arg == 'pause' or arg == 'p':
                if self.paused:
                    self.paused = False
                    self.printStats()
                    self.task_leisure_blocks += self.timer.unsplit()
                    self.leisure_blocks += self.task_leisure_blocks
                else:
                    self.paused = True
                    print (self.timer.split())
            elif arg == 'done' or arg == 'd':
                if not self.started:
                    print('[ERROR TIMER] No task to complete')
                    continue
                del self.tasks[self.curr_task_num-1]
                self.curr_task_num = None
                self.curr_task = None
                self.task_blocks = self.timer.stop()
                self.total_blocks += self.task_blocks
                self.started = False
                self.printStats()
                print ("Total: " + str(self.total_blocks))
            elif arg == 'stats':
                self.printStats()
            elif arg == 'exit':
                break
            else:
                self.printStats()

    def run(self):
        if not self.user or not self.password:
            self.user = input('Email:')
            self.password = input('Password:')
        if not self.goal_hrs and not self.goal_blocks:
            self.goal_hrs = int(input('Estimated # of hours:'))
            self.goal_blocks = self.goal_hrs * 6
        self.monitor()
        return

def main():
    if not os.path.exists(pickle_path):
        a = Application()
        a.run()
        pickle.dump(a, open(pickle_path, "wb"))
    else:
        a = pickle.load(open(pickle_path, "rb"))
        a.run()

if __name__ == "__main__":
    main()
