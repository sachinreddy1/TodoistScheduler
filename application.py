import todoist
from datetime import datetime
from pytz import timezone
from dateutil import tz
import operator
import timer
import os
import sys
import curses
import threading
import queue
import time
import todoist_scheduler

USERID = 'reddysachin2014@gmail.com'
PASSWORD = ''
api = todoist.TodoistAPI()

class Application:
    def __init__ (self):
        self.user = USERID
        self.password = PASSWORD
        self.timer = timer.Timer()
        
        self.q = queue.LifoQueue()
        
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

    def drawMonitor(self, stdscr):
        t = 0
        b = 0
        k=[]
        arg = ''
        
        stdscr.clear()
        stdscr.refresh()
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
    
        while True:
            stdscr.clear()
            if self.started:
                if self.paused:
                    t, b = self.timer.elapsedPause()
                    self.task_leisure_blocks = b
                else:
                    t, b = self.timer.elapsed()
                    self.task_blocks = b
        
            height, width = stdscr.getmaxyx()
            
            title = "---  Task Tracker  ---"[:width-1]
            now = "Now:"[:width-1]
            
            if self.curr_task:
                currTask = "{}".format(self.curr_task[0][1])
            else:
                currTask = "{}".format(self.curr_task)
            
            upNext = "Up Next:"[:width-1]
            nextTasks = self.tasks
            
            stats = "Statistics:"[:width-1]
            goal = "Goal:"[:width-1]
            goalhrs = "Hours: {}".format(self.goal_hrs)
            goalblocks = "Blocks: {}".format(self.goal_blocks)
            progress = "Progress:"[:width-1]
            progressblocks = "Blocks: {}/{}".format(self.total_blocks, self.goal_blocks)
            breakblocks = "Break Blocks: {}".format(self.leisure_blocks)
            percent = round(float(self.total_blocks) / float(self.goal_blocks) * 100.0, 2)
            pcent = "Percent: {}%".format(percent)
            tasks = "Tasks: {}/{}".format(self.num_tasks-len(self.tasks),self.num_tasks)
            
            status = "IDLE"
            if self.started:
                if self.paused:
                    status = "BREAK"
                else:
                    status = "WORKING"
        
            statusbarstr = "Press 'q' to exit | {} | Time: {} | Blocks: {}".format(status, t, b)
            
            start_x_title = int((width // 2) - (len(title) // 2) - len(title) % 2)
            start_y = 0
            
            while self.q.qsize() != 0:
                v = self.q.get()
                v_ = chr(v)
                k.append(v_)
            if k:
                if k[-1] == '\n':
                    k=[]
                elif k[0] == 'q':
                    return
                arg = " ".join(k)
            
            # Render the status bar
            stdscr.attron(curses.color_pair(3))
            stdscr.addstr(height-1, 0, statusbarstr)
            stdscr.addstr(height-1, len(statusbarstr), " " * (width - len(statusbarstr) - 1))
            stdscr.attroff(curses.color_pair(3))
            
            # Turning on attributes for title
            stdscr.attron(curses.color_pair(2))
            stdscr.attron(curses.A_BOLD)
            
            # Rendering title
            stdscr.addstr(start_y, start_x_title, title)
            
            # Turning off attributes for title
            stdscr.attroff(curses.color_pair(2))
            stdscr.attroff(curses.A_BOLD)
            
            # Print rest of text
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(start_y + 1, 0, now)
            stdscr.attroff(curses.A_BOLD)
            stdscr.addstr(start_y + 2, 0, currTask)
            
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(start_y + 4, 0, upNext)
            stdscr.attroff(curses.A_BOLD)
            
            for idx, i in enumerate(nextTasks):
                if i == self.curr_task:
                    stdscr.attron(curses.color_pair(4))
                    stdscr.attron(curses.A_BOLD)
                    stdscr.addstr(start_y + 5 + idx, 0, "{}. {}".format(idx+1, i[0][1]))
                    stdscr.attroff(curses.color_pair(4))
                    stdscr.attroff(curses.A_BOLD)
                else:
                    stdscr.addstr(start_y + 5 + idx, 0, "{}. {}".format(idx+1, i[0][1]))
            offset = start_y + 5 + len(nextTasks)
                
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(start_y+1, width-len(stats)-1, stats)
            stdscr.attroff(curses.A_BOLD)
            
            stdscr.attron(curses.color_pair(4))
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(start_y+3, width-len(goal)-1, goal)
            stdscr.attroff(curses.color_pair(4))
            stdscr.attroff(curses.A_BOLD)
            
            stdscr.addstr(start_y+4, width-len(goalhrs)-1, goalhrs)
            stdscr.addstr(start_y+5, width-len(goalblocks)-1, goalblocks)
            
            stdscr.attron(curses.color_pair(4))
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(start_y+7, width-len(progress)-1, progress)
            stdscr.attroff(curses.color_pair(4))
            stdscr.attroff(curses.A_BOLD)
            
            stdscr.addstr(start_y+8, width-len(progressblocks)-1, progressblocks)
            stdscr.addstr(start_y+9, width-len(breakblocks)-1, breakblocks)
            stdscr.addstr(start_y+10, width-len(pcent)-1, pcent)
            stdscr.addstr(start_y+11, width-len(tasks)-1, tasks)
            
            #
            iput = "--> {}".format(arg)
            stdscr.addstr(height-3, 0, iput)
            stdscr.move(height-3, len(iput))
            #
            
            if arg:
                if arg.startswith('g'):
                    self.getTasks()
                    k=[]
                    arg = ''
                elif len(k) == 2 and arg.startswith('s'):
                    t = int(k[1])
                    if t - 1 >= 0 and t - 1 < len(self.tasks):
                        self.curr_task_num = t
                        self.curr_task = self.tasks[self.curr_task_num-1]
                        self.curr_item = self.items[self.curr_task_num-1]
                        self.timer = timer.Timer()
                        k=[]
                        arg = ''
                    self.timer.start()
                    self.started = True
                elif arg.startswith('p'):
                    if self.paused:
                        self.paused = False
                        self.task_leisure_blocks = self.timer.unsplit()
                        self.leisure_blocks += self.task_leisure_blocks
                    else:
                        self.paused = True
                        msg, blocks = self.timer.split()
                        self.total_blocks += blocks
                    k=[]
                    arg = ''
                elif arg.startswith('d'):
                    if not self.started:
                        error_msg = "[ERROR TIMER] No task to complete."
                        stdscr.addstr(height - 5, 0, error_msg)
                        continue
                    del self.tasks[self.curr_task_num-1]
                    self.completeItem()
                    self.curr_task_num = None
                    self.curr_task = None
                    self.task_blocks = self.timer.stop()
                    self.total_blocks += self.task_blocks
                    self.started = False
                    k=[]
                    arg = ''
                elif arg.startswith('t'):
                    self.clearCache()
                    k=[]
                    arg = ''
                    break
                else:
                    pass

            time.sleep(0.1)
            stdscr.refresh()

    def inputting(self, stdscr):
        while True:
            time.sleep(0.1)
            if self.q.qsize() == 0:
                k = stdscr.getch()
                self.q.put(k)
                if k == ord('q'):
                    return

    def completeItem(self):
        item = api.items.get_by_id(self.curr_task[0][0])
        item.complete()
        api.commit()

    def clearCache(self):
        if os.path.exists(todoist_scheduler.pickle_path):
            os.remove(todoist_scheduler.pickle_path)
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
        
        t1 = threading.Thread(target=curses.wrapper, args=(self.inputting,))
        t2 = threading.Thread(target=curses.wrapper, args=(self.drawMonitor,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        return
