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
import getpass
from globs import *

api = todoist.TodoistAPI()
q = queue.LifoQueue()

class Application:
    def __init__ (self):
        self.user = USERID
        self.password = PASSWORD
        self.timer = timer.Timer()
        self.started = False
        self.paused = False
        
        self.total_blocks = 0
        self.break_blocks = 0
        self.total_time = 0
        self.break_time = 0
        
        self.items = []
        self.tasks = []
        self.curr_task_num = None
        self.curr_task = None
        self.curr_item = None
        
        # are these necessary?
        self.task_blocks = 0
        self.task_break_blocks = 0
        
        self.goal_hrs = 0
        self.goal_blocks = 0
    
    def get_todays_tasks(self):
        time.sleep(1)
        api.user.login(self.user, self.password)
        time.sleep(1)
        response = api.sync()
        time.sleep(1)
        today = datetime.now(timezone('EST')).strftime("%a %d %b")
        for item in response['items']:
            due = item['due_date_utc']
            if due:
                due_est = self.datetimeConverter(due)
                if due_est == today:
                    self.items.append(item)
    
    def getTasks(self):
        self.get_todays_tasks()
        if not self.items:
            return
        d = self.task_formatter(self.items)
        self.tasks = sorted(d.items(), key=operator.itemgetter(1), reverse=False)
        self.num_tasks = len(self.tasks)

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
        global q
        stdscr.clear()
        t = 0
        b = 0
        k=[]
        arg = ''
        
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
                    self.task_break_blocks = b
                else:
                    t, b = self.timer.elapsed()
                    self.task_blocks = b
        
            height, width = stdscr.getmaxyx()
            title = "---  Task Tracker  ---"[:width-1]
            now = "Now:"[:width-1]
            
            if self.curr_task:
                currTask = "{}".format(self.curr_task[0][1])
            
            upNext = "Up Next:"[:width-1]
            nextTasks = self.tasks
            
            help = "Help:"[:width-1]
            help_1 = "-> start: s [task #]"[:width-1]
            help_2 = "-> pause/unpause: p"[:width-1]
            help_3 = "-> complete: d"[:width-1]
            help_4 = "-> get: g "[:width-1]
            help_5 = "-> clear: t"[:width-1]
            
            stats = "Statistics:"[:width-1]
            goal = "Goal:"[:width-1]
            goalhrs = "Hours: {}".format(self.goal_hrs)
            goalblocks = "Blocks: {}".format(self.goal_blocks)
            
            progress = "Progress:"[:width-1]
            progressblocks = "Blocks: {}/{}".format(self.total_blocks, self.goal_blocks)
            breakblocks = "Break Blocks: {}".format(self.break_blocks)
            percent = round(float(self.total_blocks) / float(self.goal_blocks) * 100.0, 2)
            pcent = "Percent: {}%".format(percent)
            tasks = "Tasks: {}/{}".format(self.num_tasks-len(self.tasks),self.num_tasks)
            
            timestring = "Time:"[:width-1]
            
            tsec, sec = divmod(self.total_time, 60)
            hr, min = divmod(tsec, 60)
            totalTime = "Working Time: %d:%02d:%02d" % (hr, min, sec)
            
            tsec_, sec_ = divmod(self.break_time, 60)
            hr_, min_ = divmod(tsec_, 60)
            breakTime = "Break Time: %d:%02d:%02d" % (hr_, min_, sec_)
            
            addstring = "+ {}".format('-'*len(totalTime))
            
            total_tsec_, total_sec_ = divmod(self.break_time + self.total_time, 60)
            total_hr_, total_min_ = divmod(total_tsec_, 60)
            totalTime_ = "Total Time: %d:%02d:%02d" % (total_hr_, total_min_, total_sec_)
            
            if self.total_time == 0 or self.break_time == 0:
                eff = "N/A"
            else:
                eff = round(float(self.total_time) / float(self.break_time), 2)
            efficiency = "Efficiency: {}".format(eff)
            
            status = "IDLE"
            if self.started:
                if self.paused:
                    status = "BREAK"
                else:
                    status = "WORKING"
        
            statusbarstr = "Press 'q' to exit | {} | Time: {} | Blocks: {}".format(status, t, b)
            filling = " "*((width-len(statusbarstr))//2 - len(statusbarstr)%2)
            statusbarstr = filling + statusbarstr
            
            start_x_title = int((width // 2) - (len(title) // 2) - len(title) % 2)
            start_y = 0
            
            while q.qsize() != 0:
                v = q.get()
                v_ = chr(v)
                if v_ in LETTERS or v_ == '\n' or v_.isdigit():
                    k.append(v_)
                        
            if k:
                if k[-1] == '\n':
                    k=[]
                elif k[0] == 'q':
                    stdscr.clear()
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
            if self.curr_task:
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
            stdscr.addstr(offset+1, 0, help)
            stdscr.attroff(curses.A_BOLD)
            
            stdscr.addstr(offset+2, 0, help_1)
            stdscr.addstr(offset+3, 0, help_2)
            stdscr.addstr(offset+4, 0, help_3)
            stdscr.addstr(offset+5, 0, help_4)
            stdscr.addstr(offset+6, 0, help_5)
                
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
            stdscr.addstr(start_y+12, width-len(efficiency)-1, efficiency)
            
            stdscr.attron(curses.color_pair(4))
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(start_y+14, width-len(timestring)-1, timestring)
            stdscr.attroff(curses.color_pair(4))
            stdscr.attroff(curses.A_BOLD)
            
            stdscr.addstr(start_y+15, width-len(totalTime)-1, totalTime)
            stdscr.addstr(start_y+16, width-len(breakTime)-1, breakTime)
            stdscr.addstr(start_y+17, width-len(addstring)-1, addstring)
            stdscr.addstr(start_y+18, width-len(totalTime_)-1, totalTime_)
            
            iput = "--> {}".format(arg)
            stdscr.addstr(height-3, 0, iput)
            stdscr.move(height-3, len(iput))
            
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
                        time_, blocks_ = self.timer.unsplit()
                        self.break_time += self.getTotalSeconds(time_)
                        self.break_blocks += blocks_
                    else:
                        self.paused = True
                        time_, blocks_ = self.timer.split()
                        self.total_time += self.getTotalSeconds(time_)
                        self.total_blocks += blocks_
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
                    time_, blocks_ = self.timer.stop()
                    self.total_time += self.getTotalSeconds(time_)
                    self.total_blocks += blocks_
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

            stdscr.refresh()
            time.sleep(0.125)

    def inputting(self, stdscr):
        global q
        while True:
            time.sleep(0.125)
            if q.qsize() == 0:
                k = stdscr.getch()
                k_ = chr(k)
                if k_ in LETTERS or k_ == '\n' or k_.isdigit():
                    q.put(k)
                    if k_ == 'q':
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
        if len(self.user) == 0:
            self.user = input('Email: ')
        if len(self.password) == 0:
            self.password = getpass.getpass('Password: ')

        if not self.started:
            self.getTasks()

        if not self.goal_hrs and not self.goal_blocks:
            self.goal_hrs = int(input('Estimated # of hours:'))
            self.goal_blocks = self.goal_hrs * int(MIN_IN_HR / BLOCK_LEN)
        
        t1 = threading.Thread(target=curses.wrapper, args=(self.inputting,))
        t2 = threading.Thread(target=curses.wrapper, args=(self.drawMonitor,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    def getTotalSeconds(self, s):
        tp=s.split(':')
        h = int(tp[0])
        m = int(tp[1])
        s = int(tp[2].split('.')[0])
        return (h * 60 + m) * 60 + s
