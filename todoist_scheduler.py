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
        if item['content'] == '3 Cracking the Code Interview Assessments':
            print (item)
        due = item['due_date_utc']
        if due:
            # Slicing :10 gives us the relevant parts
            if due[:10] == today:
                tasks_today.append(item)

    return tasks_today

def main():
    v = get_todays_tasks('reddysachin2014@gmail.com', 'Atlas123')
    for i in v:
        print(i['content'])

if __name__ == "__main__":
    main()
