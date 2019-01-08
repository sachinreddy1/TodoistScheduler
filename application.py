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
import signal
import _pickle as pickle

api = todoist.TodoistAPI()
q = queue.LifoQueue()

def handler(signum, frame):
    raise Exception

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
        self.productive_time = 0
        
        self.items = []
        self.tasks = []
        self.curr_task_num = None
        self.curr_task = None
        
        self.task_blocks = 0
        self.task_break_blocks = 0
        self.task_time = 0
        self.task_break_time = 0
        
        self.goal_hrs = 0
        self.goal_blocks = 0
        
        self.sync_status = None
    
    def get_todays_tasks(self):
        tasks = []
        response = None
        items = None
        while not response:
            try:
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(2)
                response = api.sync()
                items = response['items']
                signal.alarm(0)
            except:
                signal.alarm(0)
        if items:
            today = datetime.now(timezone('EST')).strftime("%a %d %b")
            for item in items:
                due = item['due_date_utc']
                if due:
                    due_est = self.datetimeConverter(due)
                    if due_est == today:
                        tasks.append(item)
        return tasks

    def getTasks(self):
        t = []
        f = False
        l = self.get_todays_tasks()
        if l:
            self.items = l
            d = self.task_formatter(self.items)
            t = sorted(d.items(), key=operator.itemgetter(1), reverse=False)
            return t

    def userLogin(self):
        f = False
        while not f:
            try:
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(3)
                api.user.login(self.user, self.password)
                signal.alarm(0)
                f = True
            except:
                signal.alarm(0)

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
        stdscr.refresh()
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
                    self.task_break_time = self.getTotalSeconds(t)
                    self.task_break_blocks = b
                else:
                    t, b = self.timer.elapsed()
                    self.task_time = self.getTotalSeconds(t)
                    self.task_blocks = b
        
            height, width = stdscr.getmaxyx()
            title = "---  Task Tracker  ---"[:width-1]
            now = "Now:"[:width-1]
            
            if self.curr_task:
                currTask = "{}".format(self.curr_task[0][1])
            
            upNext = "Up Next:"[:width-1]
            help = "Help:"[:width-1]
            help_1 = "-> start: s [task #]"[:width-1]
            help_2 = "-> pause/unpause: p"[:width-1]
            help_3 = "-> complete: c"[:width-1]
            help_4 = "-> get: g "[:width-1]
            help_5 = "-> terminate: t"[:width-1]
            help_6 = "-> save: #"[:width-1]
            
            stats = "Statistics:"[:width-1]
            goal = "Goal:"[:width-1]
            goalhrs = "Hours: {}".format(self.goal_hrs)
            goalblocks = "Blocks: {}".format(self.goal_blocks)
            
            progress = "Progress:"[:width-1]
            progressblocks = "Blocks: {}/{}".format(self.total_blocks+self.task_blocks, self.goal_blocks)
            breakblocks = "Break Blocks: {}".format(self.break_blocks+self.task_break_blocks)
            percent = round(float(self.total_blocks+self.task_blocks) / float(self.goal_blocks) * 100.0, 2)
            pcent = "Percent: {}%".format(percent)
            tasks = "Tasks: {}/{}".format(self.num_tasks-len(self.tasks),self.num_tasks)
            
            timestring = "Time:"[:width-1]
            
            tsec, sec = divmod(self.total_time+self.task_time, 60)
            hr, min = divmod(tsec, 60)
            totalTime = "Working: %d:%02d:%02d" % (hr, min, sec)
            
            tsec, sec = divmod(self.productive_time, 60)
            hr, min = divmod(tsec, 60)
            prodTime = "Productive: %d:%02d:%02d" % (hr, min, sec)
            status = "IDLE"
            if self.started:
                if self.paused:
                    status = "BREAK"
                else:
                    status = "WORKING"
                    tsec, sec = divmod(self.task_time, 60)
                    hr, min = divmod(tsec, 60)
                    if (hr > 0) or (min >= STREAK_LEN):
                        status = "* " + status
                        status += " *"
                        tsec, sec = divmod(self.productive_time + (self.task_time - (STREAK_LEN*60)), 60)
                        hr, min = divmod(tsec, 60)
                        prodTime = "Productive: %d:%02d:%02d" % (hr, min, sec)
            else:
                t = datetime.now(timezone('EST')).strftime("0:00:00.000000")
                        
            tsec_, sec_ = divmod(self.break_time+self.task_break_time, 60)
            hr_, min_ = divmod(tsec_, 60)
            breakTime = "Break Time: %d:%02d:%02d" % (hr_, min_, sec_)
            
            addstring = "+ {}".format('-'*len(totalTime))
            
            total_tsec_, total_sec_ = divmod(self.break_time + self.total_time + self.task_break_time + self.task_time, 60)
            total_hr_, total_min_ = divmod(total_tsec_, 60)
            totalTime_ = "Total Time: %d:%02d:%02d" % (total_hr_, total_min_, total_sec_)
            
            if (self.total_time+self.task_time) == 0 or (self.break_time+self.task_break_time) == 0:
                eff = "N/A"
                efficiency = "Efficiency: {}".format(eff)
            else:
                eff = round(float(self.total_time+self.task_time) / float(self.break_time+self.task_break_time), 2)
                efficiency = "Efficiency: {0:.2f}".format(eff)
        
            statusbarstr = "Press 'q' to exit | {} | Time: {} | Blocks: {}".format(status, t[:7], b)
            filling = " "*((width-len(statusbarstr))//2 - len(statusbarstr)%2)
            statusbarstr = filling + statusbarstr
            
            start_x_title = int((width // 2) - (len(title) // 2) - len(title) % 2)
            start_y = 0
            
            while q.qsize() != 0:
                v = q.get()
                v_ = chr(v)
                if v_ in LETTERS or v_ == '\n' or v_.isdigit() or v == ord('#'):
                    k.append(v_)
            if k:
                if k[-1] == '\n':
                    self.sync_status = None
                    k=[]
                elif k[0] == 'q':
                    stdscr.clear()
                    return
                elif k[0] == 'g':
                    stdscr.clear()
                    return
                arg = "".join(k)
            
            stdscr.attron(curses.color_pair(3))
            stdscr.addstr(height-1, 0, statusbarstr)
            stdscr.addstr(height-1, len(statusbarstr), " " * (width - len(statusbarstr) - 1))
            stdscr.attroff(curses.color_pair(3))
            
            stdscr.attron(curses.color_pair(2))
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(start_y, start_x_title, title)
            stdscr.attroff(curses.color_pair(2))
            stdscr.attroff(curses.A_BOLD)
            
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(start_y + 1, 0, now)
            stdscr.attroff(curses.A_BOLD)
            if self.curr_task:
                stdscr.addstr(start_y + 2, 0, currTask)
            
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(start_y + 4, 0, upNext)
            stdscr.attroff(curses.A_BOLD)
            
            for idx, i in enumerate(self.tasks):
                if i == self.curr_task:
                    stdscr.attron(curses.color_pair(4))
                    stdscr.attron(curses.A_BOLD)
                    stdscr.addstr(start_y + 5 + idx, 0, "{}. {}".format(idx+1, i[0][1]))
                    stdscr.attroff(curses.color_pair(4))
                    stdscr.attroff(curses.A_BOLD)
                else:
                    stdscr.addstr(start_y + 5 + idx, 0, "{}. {}".format(idx+1, i[0][1]))
            offset = start_y + 5 + len(self.tasks)
            
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(offset+1, 0, help)
            stdscr.attroff(curses.A_BOLD)
            
            stdscr.addstr(offset+2, 0, help_1)
            stdscr.addstr(offset+3, 0, help_2)
            stdscr.addstr(offset+4, 0, help_3)
            stdscr.addstr(offset+5, 0, help_4)
            stdscr.addstr(offset+6, 0, help_5)
            stdscr.addstr(offset+7, 0, help_6)
                
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

            stdscr.addstr(start_y+20, width-len(prodTime)-1, prodTime)
            
            iput = "--> {}".format(arg)
            stdscr.addstr(height-3, 0, iput)
            if self.sync_status:
                stdscr.addstr(height-3, width-len(self.sync_status)-1, self.sync_status)
            stdscr.move(height-3, len(iput))
            
            if arg:
                if len(k) == 2 and arg.startswith('s'):
                    t = int(k[1])
                    if t - 1 >= 0 and t - 1 < len(self.tasks):
                        self.curr_task_num = t
                        self.curr_task = self.tasks[self.curr_task_num-1]
                        self.timer = timer.Timer()
                        k=[]
                        arg = ''
                    self.timer.start()
                    self.started = True
                elif arg.startswith('p'):
                    if self.paused:
                        self.paused = False
                        time_, blocks_ = self.timer.unsplit()
                        self.task_break_blocks = 0
                        self.task_break_time = 0
                        self.break_blocks += blocks_
                        self.break_time += self.getTotalSeconds(time_)
                    else:
                        self.paused = True
                        time_, blocks_ = self.timer.split()
                        tsec, sec = divmod(self.task_time, 60)
                        hr, min = divmod(tsec, 60)
                        if (hr > 0) or (min >= STREAK_LEN):
                            self.productive_time = self.productive_time + (self.task_time - (STREAK_LEN*60))
                        self.task_blocks = 0
                        self.task_time = 0
                        self.total_blocks += blocks_
                        self.total_time += self.getTotalSeconds(time_)

                    k=[]
                    arg = ''
                elif arg.startswith('c'):
                    if not self.started:
                        k=[]
                        arg = ''
                        pass
                    else:
                        self.completeItem()
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
                elif arg.startswith('#'):
                    k=[]
                    arg = ''
                    pickle.dump(self, open(pickle_path, "wb"))
                    self.sync_status = "Saved."
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
                if k_ in LETTERS or k_ == '\n' or k_.isdigit() or k == ord('#'):
                    q.put(k)
                    if k_ == 'g':
                        return False
                    if k_ == 'q':
                        return True

    def completeItem(self):
        item = None
        while not item:
            item = api.items.get_by_id(self.curr_task[0][0])
            item.complete()
            api.commit()
        del self.tasks[self.curr_task_num-1]
        self.curr_task_num = None
        self.curr_task = None


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
            self.userLogin()
            self.tasks = self.getTasks()
            self.num_tasks = len(self.tasks)

        if not self.goal_hrs and not self.goal_blocks:
            self.goal_hrs = int(input('Estimated # of hours:'))
            self.goal_blocks = self.goal_hrs * int(MIN_IN_HR / BLOCK_LEN)

        f = False
        while not f:
            t1 = threading.Thread(target=curses.wrapper, args=(self.drawMonitor,))
            t1.start()
            f = curses.wrapper(self.inputting)
            t1.join()
            if not f:
                l = self.getTasks()
                if l:
                    self.sync_status = "+ {} tasks".format(len(l))
                    if self.tasks:
                        for i in l:
                            self.tasks.append(i)
                            self.num_tasks = len(self.tasks)
                    else:
                        self.tasks = l
                        self.num_tasks = len(self.tasks)
                else:
                    self.sync_status = "+ 0 tasks"

    def getTotalSeconds(self, s):
        tp=s.split(':')
        h = int(tp[0])
        m = int(tp[1])
        s = int(tp[2].split('.')[0])
        return (h * 60 + m) * 60 + s
