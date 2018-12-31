import todoist
from datetime import datetime
from dateutil import tz
import queue
import threading
import operator
import time

api = todoist.TodoistAPI()
USERID = 'reddysachin2014@gmail.com'
PASSWORD = ''

class Timer(object):
    def __init__(self):
        self.pausestart = 0.0
        self.elapsedpause = 0.0
        pass
    
    def start(self, message="Started at: "):
        self.start = datetime.now()
        msg = str(self.start).split(' ')[1]
        return message + msg
    
    def stop(self, message="Total: "):
        self.stop = datetime.now()
        return message + str(self.stop - self.start)
    
    def now(self, message="Now: "):
        return message + ": " + str(datetime.now())
    
    def elapsed(self, message="Elapsed: "):
        return message + str(datetime.now() - self.start)
    
    def split(self, message="Pause at: "):
        self.split_start = datetime.now()
        return message + str(self.split_start).split(' ')[1]
    
    def unsplit(self, message="Elapsed pause: "):
        msg = str(datetime.now() - self.split_start)
        return message + msg

class Application:
    def __init__ (self):
        self.user = USERID
        self.password = PASSWORD
        self.timer = Timer()

    def get_todays_tasks(self, email, password):
        api.user.login(email, password)
        tasks_today = []
        response = api.sync()
        today = datetime.utcnow().strftime("%a %d %b")
        for item in response['items']:
            due = item['due_date_utc']
            if due:
                due_est = self.datetimeConverter(due)
                if due_est == today:
                    tasks_today.append(item)
        return tasks_today
    
    def getTasks(self):
        v = self.get_todays_tasks(USERID, PASSWORD)
        d = self.task_formatter(v)
        l = self.sortTasks(d)
        return l
    
    def sortTasks(self, d):
        l = []
        l = sorted(d.items(), key=operator.itemgetter(1))
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
        print("============  Up Next:  ============")
        for idx, i in enumerate(items):
            id = i[0][0]
            content = i[0][1]
            print("| {0}. {1}".format((idx+1), content))
        print("====================================")

    def monitor(self):
        helper = '''
            ======  Command List  ======
            - get / g (get tasks from Todoist's server)
            - start / s
            - pause / p
            - done / d
            - stats
            - stop
            ============================
            '''
        print(helper)
        paused = False
        while True:
            arg = input('-->')
            args = arg.split(' ')
            if arg == '?' or arg == 'help':
                print(helper)
            elif arg == 'get' or arg.startswith('g'):
                t = self.getTasks()
                self.printItems(t)
            elif arg == 'start' or arg == 's':
                print (self.timer.start())
            elif arg == 'pause' or arg == 'p':
                if paused:
                    paused = False
                    print (self.timer.unsplit())
                else:
                    paused = True
                    print (self.timer.split())
            elif arg == 'done' or arg == 'd':
                print (self.timer.stop())
            elif arg == 'stats':
                print("--")
            else:
                print('[ERROR] Invalid input arg %s' % arg)


def main():
    a = Application()
    a.monitor()


if __name__ == "__main__":
    main()
