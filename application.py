# coding: utf-8

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
import subprocess
import signal
import sys
if sys.version_info[0] < 3:
    import pickle as pickle
else:
    import _pickle as pickle

q = queue.LifoQueue()

def handler(signum, frame):
    raise Exception

class Storage:
    def __init__(self):
        self.d = {}

class Application:
    def __init__ (self):
        self.api = todoist.TodoistAPI()
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
        self.hour_track = 0
        self.sync_status = None
        self.sync_status_time = None
        self.today = datetime.now(timezone('EST')).strftime("%a %d %b")
        self.num_tasks = None
    
    def get_todays_tasks(self):
        tasks = []
        response = None
        items = None
        print('Syncing...')
        while not response:
            try:
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(2)
                response = self.api.sync()
                items = response['items']
                signal.alarm(0)
            except:
                signal.alarm(0)
            if response and 'error_tag' in response and response['error_tag'] == 'AUTH_INVALID_TOKEN':
                waitval = response['error_extra']['retry_after']
                time.sleep(waitval)
                self.userLogin()
                response = None
        if items:
            today = datetime.now(timezone('EST')).strftime("%a %d %b")
            for item in items:
                due = item['due_date_utc']
                if due:
                    due_est = self.datetimeConverter(due, "%a %d %b")
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
                self.api.user.login(self.user, self.password)
                signal.alarm(0)
                f = True
            except:
                signal.alarm(0)

    def datetimeConverter(self, due, format):
        from_zone = tz.tzutc()
        to_zone = tz.tzlocal()
        utc = datetime.strptime(due, "%a %d %b %Y %H:%M:%S +0000")
        utc = utc.replace(tzinfo=from_zone)
        utc = utc.replace(tzinfo=from_zone)
        central = utc.astimezone(to_zone).strftime(format)
        return central
    
    def getTotalSeconds(self, s):
        tp=s.split(':')
        h = int(tp[0])
        m = int(tp[1])
        s = int(tp[2].split('.')[0])
        return (h * 60 + m) * 60 + s
    
    def task_formatter(self, items):
        d = {}
        for i in items:
            id = i['id']
            content = i['content']
            date_est = self.datetimeConverter(i['due_date_utc'], "%H:%M:%S")
            priority = i['priority']
            d[(id, content)]=(date_est, -priority)
        return d

    def drawMonitor(self, stdscr):
        global q
        
        # refresh and clear the screen
        stdscr.clear()
        stdscr.refresh()
        # Init
        t = "0:00:00.000000"
        b = 0
        acc_hour_blocks = 0
        k=[]
        arg = ""
        argval = ""
#        store = self.store
        screen_flag = False
        self.playing = False
        
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
    
        while True:
            stdscr.clear()
            # started and paused conditions - getting values
            try:
                if self.started and self.paused:
                    t, b = self.timer.elapsedPause()
                    self.task_break_time = self.getTotalSeconds(t)
                    self.task_break_blocks = b
                else:
                    t, b = self.timer.elapsed()
                    self.task_time = self.getTotalSeconds(t)
                    self.task_blocks = b
            except:
                pass
        
            # getting height and width values of terminal
            height, width = stdscr.getmaxyx()
            # Getting string values for screen
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
            help_5 = "-> save: #"[:width-1]
            help_6 = "-> records: r"[:width-1]
            
            stats = "Statistics:"[:width-1]
            goal = "Goal:"[:width-1]
            goalhrs = "Hours: {}".format(self.goal_hrs)
            goalblocks = "Blocks: {}".format(self.goal_blocks)
            
            progress = "Progress:"[:width-1]
            progressblocks = "Blocks: {}/{}".format(self.total_blocks+self.task_blocks, self.goal_blocks)
            breakblocks = "Break Blocks: {}".format(self.break_blocks+self.task_break_blocks)
            percent = round(float(self.total_blocks+self.task_blocks) / float(self.goal_blocks) * 100.0, 2)
            pcent = "Percent: {}%".format(percent)
            if self.tasks:
                tasks = "Tasks: {}/{}".format(self.num_tasks-len(self.tasks),self.num_tasks)
            else:
                tasks = "Tasks: {}/{}".format(0,self.num_tasks)
            
            # Calculating times for menu
            timestring = "Time:"[:width-1]
            tsec, sec = divmod(self.total_time+self.task_time, 60)
            hr, min = divmod(tsec, 60)
            totalTime = "Working: %d:%02d:%02d" % (hr, min, sec)
            tsec, sec = divmod(self.productive_time, 60)
            hr, min = divmod(tsec, 60)
            prodTime = "Productive: %d:%02d:%02d" % (hr, min, sec)
            tsec_, sec_ = divmod(self.break_time+self.task_break_time, 60)
            hr_, min_ = divmod(tsec_, 60)
            breakTime = "Break: %d:%02d:%02d" % (hr_, min_, sec_)
            
            # Total Time calculatiaons and formatting
            addstring = "+ {}".format('-'*len(totalTime))
            total_tsec_, total_sec_ = divmod(self.break_time + self.total_time + self.task_break_time + self.task_time, 60)
            total_hr_, total_min_ = divmod(total_tsec_, 60)
            totalTime_ = "Total: %d:%02d:%02d" % (total_hr_, total_min_, total_sec_)
            
            # Status setter and productive calculations
            status = "IDLE"
            if self.started and self.paused:
                status = "BREAK"
                tsec, sec = divmod(self.task_break_time, 60)
                hr, min = divmod(tsec, 60)
                if (hr > 0) or (min >= BREAK_LEN):
                    if not self.playing:
                        subprocess.call(["afplay", "alarms/alarm_1.mp3"])
                        self.playing = True
                else:
                    self.playing = False
                
            elif self.started:
                status = "WORKING"
                tsec, sec = divmod(self.task_time, 60)
                hr, min = divmod(tsec, 60)
                if (hr > 0) or (min >= STREAK_LEN):
                    status = "{}{}{}".format("* ", status, " *")
                    tsec, prodsec = divmod(self.productive_time + (self.task_time - (STREAK_LEN*60)), 60)
                    prodhr, prodmin = divmod(tsec, 60)
                    prodTime = "Productive: %d:%02d:%02d" % (prodhr, prodmin, prodsec)
            else:
                t = "0:00:00.000000"

            # Efficiency string and formatting
            if (self.total_time+self.task_time) == 0 or (self.break_time+self.task_break_time) == 0:
                eff = "N/A"
                efficiency = "Efficiency: {}".format(eff)
            else:
                eff = round(float(self.total_time+self.task_time) / float(self.break_time+self.task_break_time), 2)
                efficiency = "Efficiency: {0:.2f}".format(eff)
                if eff < 1.0:
                    efficiency = "! - " + efficiency

            # Status bar string
            statusbarstr = "Press 'q' to exit | {} | Time: {} | Blocks: {}".format(status, t[:7], b)
            filling = " "*((width-len(statusbarstr))//2 - len(statusbarstr)%2)
            statusbarstr = filling + statusbarstr
            start_x_title = int((width // 2) - (len(title) // 2) - len(title) % 2)
            start_y = 0

            #---------------------------------------------------------------#

            # SEC CHECK: Set the sync_message back to None after 4 seconds  --  OK
            second_check = int(datetime.now(timezone('EST')).strftime("%S"))
            if self.sync_status_time:
                seconds_past = second_check - self.sync_status_time
                if seconds_past%4 == 0 and seconds_past != 0:
                    self.sync_status = None
                    self.sync_status_time = None

            # Calculating the productive values --  OK
            prod_time = self.productive_time
            if (hr > 0) or (min >= STREAK_LEN):
                prod_time = self.productive_time + (self.task_time - (STREAK_LEN*60))

            # Check the if still the same day - if not, save and reset the values   -- OK - Change later.
            day_check = datetime.now(timezone('EST')).strftime("%a %d %b")
            if self.today != day_check:
                pickle.dump(self, open(pickle_path, "wb"))
                pickle.dump(self.store, open(pickle_data_path, "wb"))
                self.today = day_check

            #---------------------------------------------------------------#

            # UNDER CONSTRUCTION:
            # Store value in dictionary - should only write at end of the hour
            hour_check = datetime.now(timezone('EST')).strftime("%M")
            if hour_check == "00":
                self.hour_track = self.total_blocks
                acc_hour_blocks = self.total_blocks
            new_now = datetime.now(timezone('EST')).strftime("%b %d: %H")
            self.store[new_now] = {
                'total_blocks': self.total_blocks + self.task_blocks,
                'break_blocks': self.break_blocks + self.task_break_blocks,
                'percent': percent,
                'efficiency': eff,
                'total_time': self.total_time + self.task_time,
                'break_time': self.break_time + self.task_break_time,
                'productive_time': self.productive_time,
                'hour_blocks': (self.total_blocks + self.task_blocks) - self.hour_track,
                'acc_hour_blocks': acc_hour_blocks
            }

            #---------------------------------------------------------------#

            # Check the q, get the character and add to the k list
            while q.qsize() != 0:
                v_ = chr(q.get())
                if ord(v_) != 127:
                    k.append(v_)
                elif k:
                    del k[-1]
                    arg = arg[:-1]

                if v_ == '\n':
                    argval = arg
                    arg = ""
                    self.sync_status = None
                    self.sync_status_time = None
                    percent = round(float(self.total_blocks+self.task_blocks) / float(self.goal_blocks) * 100.0, 2)
                    new_now = datetime.now(timezone('EST')).strftime("%b %d: %H")
                    self.store[new_now] = {
                        'total_blocks': self.total_blocks + self.task_blocks,
                        'break_blocks': self.break_blocks + self.task_break_blocks,
                        'percent': percent,
                        'efficiency': eff,
                        'total_time': self.total_time + self.task_time,
                        'break_time': self.break_time + self.task_break_time,
                        'productive_time': self.productive_time,
                        'hour_blocks': (self.total_blocks + self.task_blocks) - self.hour_track,
                        'acc_hour_blocks':acc_hour_blocks
                    }
#                    pickle.dump(self, open(pickle_path, "wb"))
#                    pickle.dump(self.store, open(pickle_data_path, "wb"))
                    k=[]
                elif v_ == 'q':
                    arg = ""
                    prod_time = self.productive_time
                    if (hr > 0) or (min >= STREAK_LEN):
                        prod_time = self.productive_time + (self.task_time - (STREAK_LEN*60))
                    new_now = datetime.now(timezone('EST')).strftime("%b %d: %H")
                    self.store[new_now] = {
                        'total_blocks': self.total_blocks + self.task_blocks,
                        'break_blocks': self.break_blocks + self.task_break_blocks,
                        'percent': percent,
                        'efficiency': eff,
                        'total_time': self.total_time + self.task_time,
                        'break_time': self.break_time + self.task_break_time,
                        'productive_time': self.productive_time,
                        'hour_blocks': (self.total_blocks + self.task_blocks) - self.hour_track,
                        'acc_hour_blocks': acc_hour_blocks
                    }
                    stdscr.clear()
                    return
                elif v_ == 'g':
                    arg = ""
                    stdscr.clear()
                    return
            if k:
                arg = "".join(k)
            
            # Always print the title for the menu
            try:
                stdscr.attron(curses.color_pair(2))
                stdscr.attron(curses.A_BOLD)
                stdscr.addstr(start_y, start_x_title, title)
                stdscr.attroff(curses.color_pair(2))
                stdscr.attroff(curses.A_BOLD)
            except:
                pass

            # Based on screen flag, print different menu items
            if not screen_flag:
                try:
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
                except:
                    pass
            else:
                stdscr.attron(curses.A_BOLD)
                record = "Records:"[:width-1]
                stdscr.addstr(start_y + 1, width-len(record)-1, record)
                stdscr.attroff(curses.A_BOLD)
                record_info = "By Hour (Date: Hour | Blocks):"[:width-1]
                stdscr.addstr(start_y + 2, width-len(record_info)-1, record_info)
                
                stdscr.attron(curses.A_BOLD)
                records_day = "Past 24 Hours:"[:width-1]
                stdscr.addstr(start_y + 1, 0, records_day)
                stdscr.attroff(curses.A_BOLD)
                
                #------------------------ PAST 24 HOURS: -------------------------#
                
                dlen = len(self.store)
                day_sum = 0
                past_day_sum = 0
                
                temp_store = {k: self.store[k] for k in list(self.store)[dlen-24:]}
                
                past_temp_store = {k: self.store[k] for k in list(self.store)[dlen-48:dlen-24]}
                for label, val in temp_store.items():
                    try:
                        day_sum+=val['acc_hour_blocks']
                    except:
                        pass
                for label, val in past_temp_store.items():
                    try:
                        past_day_sum+=val['acc_hour_blocks']
                    except:
                        pass

                stdscr.addstr(start_y + 2, 0, "--> Today's Hours: {}".format(round(day_sum/60, 2)))
                stdscr.addstr(start_y + 3, 0, "--> Yesterday's Hours: {}".format(round(past_day_sum/60, 2)))
                stdscr.addstr(start_y + 4, 0, "--> Blocks: {}".format(day_sum))

                longest_label_length = max([len(label) for label, _ in self.store.items()])
                label_len = longest_label_length + len(" ▏ ## ")
                max_value = max([x['hour_blocks'] for _, x in self.store.items()])
                increment = 1
                if max_value != 0:
                    increment = max_value /((width-label_len)-(width/2)-1)
                
                #----------------------- RECORDING BLOCKS: ---------------------------#

                count_ = 0
                if dlen >= 24:
                    temp_store = {k: self.store[k] for k in list(self.store)[dlen-24:]}
                    for label, val in temp_store.items():
                        count = val['hour_blocks']
                        bar_chunks, remainder = divmod(int(count * 8 / increment), 8)
                        bar = '█' * bar_chunks
                        if remainder > 0:
                            bar += chr(ord('█') + (8 - remainder))
                        bar = bar or  '▏'
                        v = f'{label.rjust(longest_label_length)} ▏ {count:#3d} {bar}'
                        try:
                            if label == list(self.store)[len(self.store)-1]:
                                stdscr.attron(curses.color_pair(4))
                                stdscr.attron(curses.A_BOLD)
                            stdscr.addstr(4+count_, int(width/2)-1, v)
                        except:
                            pass
                        stdscr.attroff(curses.color_pair(4))
                        stdscr.attroff(curses.A_BOLD)
                        count_+=1
                else:
                    for label, val in self.store.items():
                        count = val['hour_blocks']
                        bar_chunks, remainder = divmod(int(count * 8 / increment), 8)
                        bar = '█' * bar_chunks
                        if remainder > 0:
                            bar += chr(ord('█') + (8 - remainder))
                        bar = bar or  '▏'
                        v = f'{label.rjust(longest_label_length)} ▏ {count:#3d} {bar}'
                        try:
                            if label == list(self.store)[len(self.store)-1]:
                                stdscr.attron(curses.color_pair(4))
                                stdscr.attron(curses.A_BOLD)
                            stdscr.addstr(4+count_, int(width/2)-1, v)
                        except:
                            pass
                        stdscr.attroff(curses.color_pair(4))
                        stdscr.attroff(curses.A_BOLD)
                        count_+=1
            
            #----------------------- INPUT ---------------------------#

            # Printing the help screen, input menu, and status bar
            
            try:
                iput = "--> {}".format(arg)
                stdscr.attron(curses.A_BOLD)
                stdscr.addstr(offset+1, 0, help)
                stdscr.attroff(curses.A_BOLD)
                
                stdscr.addstr(offset+2, 0, help_1)
                stdscr.addstr(offset+3, 0, help_2)
                stdscr.addstr(offset+4, 0, help_3)
                stdscr.addstr(offset+5, 0, help_4)
                stdscr.addstr(offset+6, 0, help_5)
                stdscr.addstr(offset+7, 0, help_6)
                
                stdscr.addstr(height-3, 0, iput)
                if self.sync_status:
                    stdscr.addstr(height-3, int(width/2)-int(len(self.sync_status))-3, self.sync_status)
                
                stdscr.attron(curses.color_pair(3))
                stdscr.addstr(height-1, 0, statusbarstr)
                stdscr.addstr(height-1, len(statusbarstr), " " * (width - len(statusbarstr) - 1))
                stdscr.attroff(curses.color_pair(3))
                stdscr.move(height-3, len(iput))
            except:
                pass
                    
            
            if argval:
                if len(argval) >= 2 and argval.startswith('s') and argval[1:].isdigit():
                    t_ = int(argval[1:])
                    if t_ - 1 >= 0 and t_ - 1 < len(self.tasks):
                        self.curr_task_num = t_
                        self.curr_task = self.tasks[self.curr_task_num-1]
                        if not self.paused:
                            self.timer = timer.Timer()
                            self.timer.start()
                        self.started = True
                    argval = ""
                elif argval.startswith('p'):
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
                    argval = ""
                elif argval.startswith('c'):
                    if not self.started:
                        pass
                    else:
                        self.completeItem()
                        time_, blocks_ = self.timer.stop()
                        self.total_time += self.getTotalSeconds(time_)
                        self.total_blocks += blocks_
                        self.started = False
                    argval = ""
                elif argval.startswith('#'):
                    percent = round(float(self.total_blocks+self.task_blocks) / float(self.goal_blocks) * 100.0, 2)
                    new_now = datetime.now(timezone('EST')).strftime("%b %d: %H")
                    self.store[new_now] = {
                        'total_blocks': self.total_blocks + self.task_blocks,
                        'break_blocks': self.break_blocks + self.task_break_blocks,
                        'percent': percent,
                        'efficiency': eff,
                        'total_time': self.total_time + self.task_time,
                        'break_time': self.break_time + self.task_break_time,
                        'productive_time': self.productive_time,
                        'hour_blocks': (self.total_blocks + self.task_blocks) - self.hour_track,
                        'acc_hour_blocks':acc_hour_blocks
                    }
                    pickle.dump(self, open(pickle_path, "wb"))
                    pickle.dump(self.store, open(pickle_data_path, "wb"))
                    self.sync_status = "Saved."
                    self.sync_status_time = int(datetime.now(timezone('EST')).strftime("%S"))
                    argval = ""
                elif argval.startswith('r'):
                    if screen_flag:
                        screen_flag = False
                    else:
                        screen_flag = True
                    argval = ""
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
                try:
                    k_ = chr(k)
                    if k_ in LETTERS or k_ == '\n' or k_.isdigit() or k == ord('#') or k == 127:
                        q.put(k)
                        if k_ == 'g':
                            return False
                        elif k_ == 'q':
                            return True
                except:
                    pass

    def completeItem(self):
        item = None
        if not self.started:
            self.userLogin()
        try:
            item = self.api.items.get_by_id(self.curr_task[0][0])
            item.complete()
            self.api.commit()
        except:
            pass
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
        
        if not self.started and not self.tasks:
            self.userLogin()
            self.tasks = self.getTasks()
            if self.tasks:
                self.num_tasks = len(self.tasks)

        if os.path.exists(pickle_data_path):
            self.store = pickle.load(open(pickle_data_path, "rb"))
        else:
            self.store = Storage().d

        if not self.goal_hrs and not self.goal_blocks:
            self.goal_hrs = int(input('Estimated # of hours: '))
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
                    os.system('clear')
                    self.sync_status = "+ {} tasks".format(len(l))
                    self.sync_status_time = int(datetime.now(timezone('EST')).strftime("%S"))
                    if self.tasks:
                        for i in l:
                            self.tasks.append(i)
                            self.num_tasks = len(self.tasks)
                    else:
                        self.tasks = l
                        self.num_tasks = len(self.tasks)
                else:
                    os.system('clear')
                    self.sync_status = "+ 0 tasks"
                    self.sync_status_time = int(datetime.now(timezone('EST')).strftime("%S"))
