import todoist
from datetime import datetime
from dateutil import tz
import queue

# Log user in; switch to OAuth eventually...
api = todoist.TodoistAPI()

def get_todays_tasks(email, password):
    """
    Get tasks due on the current utc day
    :return: list of task dicts
    """
    # user = api.user.login(email, password)
    api.user.login(email, password)
    tasks_today = []
    
    # Sync (load) data
    response = api.sync()
    
    # Get "today", only keep Day XX Mon, which Todoist uses
    today = datetime.utcnow().strftime("%a %d %b")
    for item in response['items']:
        due = item['due_date_utc']
        if due:
            due_est = datetimeConverter(due)
            print("today", today)
            print ("due_est:", due_est)
            if due[:10] == today:
                tasks_today.append(item)

    return tasks_today

def datetimeConverter(due):
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    
    utc = datetime.strptime(due, "%a %d %b %Y %H:%M:%S +0000")
    utc = utc.replace(tzinfo=from_zone)
    utc = utc.replace(tzinfo=from_zone)
    central = utc.astimezone(to_zone)
    return central


def task_formatter(items):
    d = {}
    c = 1
    for i in items:
        dv = i['due_date_utc'].split(' ')[4].split(':')
        due_date_val = int(dv[0])*100 + int(dv[1])
        priority_val = i['priority']
        item_val = i['item_order']
        content = i['content']
        val = (due_date_val, priority_val, item_val)
        d[(c, content)]=val
        c+=1
    return d

def printItems(items):
    print("#------------------------------#")
    for i in items:
        due_date = i['due_date_utc'].split(' ')[4]
        print("{0}:".format(i['content']))
        print("     priority: {0}".format(i['priority']))
        print("     due_date: {0}".format(due_date))
        print("     item_num: {0}".format(i['item_order']))
        print("#------------------------------#")

def itemsQueue(items):
    q = queue.PriorityQueue()
    for i in items:
        q.put(i)
    return q

def main():
    v = get_todays_tasks('reddysachin2014@gmail.com', '')
    d = task_formatter(v)
    i = [v for k, v in d.items()]
    print (i)
    q = itemsQueue(i)
    while q.qsize() != 0:
        k = q.get()
        print(k)

if __name__ == "__main__":
    main()
