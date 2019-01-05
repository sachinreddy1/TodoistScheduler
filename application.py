import todoist
from datetime import datetime
from pytz import timezone
from dateutil import tz
import operator
import timer
import os

USERID = 'reddysachin2014@gmail.com'
PASSWORD = ''
api = todoist.TodoistAPI()

class Application:
    def __init__ (self):
        self.user = USERID
        self.password = PASSWORD
        self.timer = timer.Timer()
        
        self.started = False
        self.paused = False
        
        self.total_blocks = 0
        self.leisure_blocks = 0
        
        self.items = None
        self.tasks = None
        
        self.curr_task_num = None
        self.curr_task = None
        self.curr_item = None
        
        self.task_blocks = 0
        self.task_leisure_blocks = 0
        
        self.goal_hrs = 0
        self.goal_blocks = 0
        self.getTasks()
    
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
        temp_items = self.items
        items = self.get_todays_tasks(USERID, PASSWORD)
        if not items:
            print('[ERROR] Items not properly synced.')
            self.items = temp_items
            return
        self.items = items
        d = self.task_formatter(self.items)
        self.tasks = sorted(d.items(), key=operator.itemgetter(1), reverse=False)
        self.num_tasks = len(self.tasks)
        print("Done.")
    
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
                time, blocks = self.timer.elapsedPause()
                self.task_leisure_blocks = blocks
            else:
                time, blocks = self.timer.elapsed()
                self.task_blocks = blocks

        self.printItems(self.tasks)
        print("==========  Statistics:  ===========")
        print("|-> Goal: ")
        print("|  Hours: " + str(self.goal_hrs))
        print("|  Blocks: " + str(self.goal_blocks))
        print("|-> Progress: ")
        print("|  Blocks: " + str(self.total_blocks) + "/" + str(self.goal_blocks))
        print("|  Break Blocks: " + str(self.leisure_blocks))
        percent = round( float(self.total_blocks) / float(self.goal_blocks) * 100.0, 2)
        print("|  Percent: " + str(percent) + "%")
        print("|  Tasks: " + str(self.num_tasks - len(self.tasks)) + "/" + str(self.num_tasks))
        
        if self.started:
            if self.paused:
                print("=============  Break:  =============")
            else:
                print("============  Working:  ============")
            print("|-> {0}".format(self.curr_task[0][1]))
            print("|  Time: " + time)
            print("|  Blocks: " + str(blocks))
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
            - terminate
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
                    self.curr_item = self.items[self.curr_task_num-1]
                    self.timer = timer.Timer()
                self.printStats()
                print (self.timer.start())
                print ('Current task: ' + self.curr_task[0][1])
                self.started = True
            elif arg == 'pause' or arg == 'p':
                if self.paused:
                    self.paused = False
                    self.task_leisure_blocks = self.timer.unsplit()
                    self.leisure_blocks += self.task_leisure_blocks
                else:
                    self.paused = True
                    msg, blocks = self.timer.split()
                    self.total_blocks += blocks
                    print(msg)
                self.printStats()
            elif arg == 'done' or arg == 'd':
                if not self.started:
                    print('[ERROR TIMER] No task to complete')
                    continue
                del self.tasks[self.curr_task_num-1]
                self.completeItem()
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
            elif arg == 'terminate':
                self.clearCache()
                break
            else:
                self.printStats()

    def completeItem(self):
        item = api.items.get_by_id(self.curr_task[0][0])
        item.complete()
        api.commit()
        print('COMPLETED: ', self.curr_task[0][1])

    def clearCache(self):
        if os.path.exists(pickle_path):
            os.remove(pickle_path)
            print('Cleared Cache.')
        else:
            print('No Cache to clear.')

    def run(self):
        if not self.user or not self.password:
            self.user = input('Email:')
            self.password = input('Password:')
        if not self.goal_hrs and not self.goal_blocks:
            self.goal_hrs = int(input('Estimated # of hours:'))
            self.goal_blocks = self.goal_hrs * int(timer.MIN_IN_HR / timer.BLOCK_LEN)
        self.monitor()
        return
