import todoist
from datetime import datetime

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
            if due[:10] == today:
                tasks_today.append(item)

    return tasks_today

def main():
    v = get_todays_tasks('reddysachin2014@gmail.com', '')
    for i in v:
        due_date = i['due_date_utc'].split(' ')[4]
        print("{0}:".format(i['content']))
        print("     priority: {0}".format(i['priority']))
        print("     due_date: {0}".format(due_date))
        print("     item_num: {0}".format(i['item_order']))
        print("#------------------------------#")

if __name__ == "__main__":
    main()
