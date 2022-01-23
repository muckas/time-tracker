import logging
import os
import time
import datetime
import db
import tgbot
import constants

log = logging.getLogger('main')

def timezoned(users, user_id, timestamp):
  delta = 60 * 60 * users[user_id]['timezone']
  return timestamp + delta

def get_main_menu(users, user_id):
  active_task = users[user_id]['active_task']
  if active_task:
    start_task_button = f'{constants.get_name("stop")}{active_task["name"]}'
  else:
    start_task_button = constants.get_name('start_task')
  keyboard = [
      [start_task_button],
      [constants.get_name('add_task'), constants.get_name('remove_task')],
      [constants.get_name('task_stats'), constants.get_name('set_timezone')],
      # [constants.get_name('disable_menu')]
      ]
  if users[user_id]['timezone'] == None:
    keyboard[0] = [constants.get_name('set_timezone')]
  return keyboard

def enable_menu(user_id):
  users = db.read('users')
  change_state(users, user_id, 'main_menu')
  tgbot.send_message(user_id, 'Main menu', keyboard=get_main_menu(users, user_id))

def disable_menu(user_id):
  tgbot.send_message(user_id, 'Menu disabled', keyboard=[])

def change_state(users, user_id, new_state):
  users[user_id]['state'] = new_state
  username = users[user_id]['username']
  db.write('users', users)
  log.debug(f'New state "{new_state}" for user @{username}({user_id})')

def get_enabled_tasks(users, user_id):
  tasks = users[user_id]['tasks']
  enabled_tasks = []
  for task in tasks:
    if tasks[task]['enabled']:
      enabled_tasks.append(task)
  return enabled_tasks

def stop_task(users, user_id, task_name):
  task_start_time = users[user_id]['active_task']['start_time']
  task_end_time = int(time.time())
  write_task_to_diary(users, user_id, task_name, task_start_time, task_end_time)
  users[user_id]['last_task_end_time'] = task_end_time
  task_duration_sec = task_end_time - task_start_time
  task_duration = datetime.timedelta(seconds=task_duration_sec)
  users[user_id]['active_task'] = None
  users[user_id]['tasks'][task_name]['time_total'] += task_duration_sec
  db.write('users',users)
  return task_duration

def write_task_to_diary(users, user_id, task_name, start_time, end_time):
  timezone = users[user_id]['timezone']
  tzoffset = datetime.timezone(datetime.timedelta(hours=timezone))
  tz_start_time = timezoned(users, user_id, start_time)
  tz_end_time = timezoned(users, user_id, end_time)
  start_date = datetime.datetime.utcfromtimestamp(tz_start_time)
  end_date = datetime.datetime.utcfromtimestamp(tz_end_time)
  one_second = datetime.timedelta(seconds=1)
  while True:
    if start_date.date() == end_date.date():
      update_diary_day(users, user_id, task_name, start_date.timestamp(), end_date.timestamp(), timezone)
      break
    temp_end_date = start_date.replace(hour=23, minute=59, second=59)
    update_diary_day(users, user_id, task_name, start_date.timestamp(), temp_end_date.timestamp(), timezone)
    start_date = temp_end_date + one_second

def update_diary_day(users, user_id, task_name, tz_start_time, tz_end_time, timezone):
  start_date = datetime.datetime.utcfromtimestamp(tz_start_time)
  filename = f'{start_date.year}-{start_date.month}-{user_id}'
  diary_path = os.path.join('data', user_id, filename)
  diary = db.read(diary_path)
  tz_time_total = tz_end_time - tz_start_time
  if not diary:
    diary = constants.get_defaul_diary()
  day_number = str(start_date.day)
  if day_number not in diary['days'].keys():
    diary['days'][day_number] = constants.get_default_day(timezone)

  try:
    diary['tasks_total'][task_name] += tz_time_total
  except KeyError:
    diary['tasks_total'][task_name] = tz_time_total
  try:
    diary['days'][day_number]['tasks_total'][task_name] += tz_time_total
  except KeyError:
    diary['days'][day_number]['tasks_total'][task_name] = tz_time_total

  diary['days'][day_number]['history'].append(
      {
        'type':'task',
        'name':task_name,
        'start_time':tz_start_time,
        'end_time':tz_end_time,
        'total_time':tz_time_total
        }
      )
  db.write(diary_path, diary)

def get_task_stats(users, user_id):
  tasks = get_enabled_tasks(users, user_id)
  report = 'Total task statistics\n--------------------'
  for task in tasks:
    task_info = users[user_id]['tasks'][task]
    date_added = timezoned(users, user_id, task_info['date_added'])
    date_added = datetime.datetime.utcfromtimestamp(date_added)
    time_total = datetime.timedelta(seconds=task_info['time_total'])
    time_total_hours = task_info['time_total'] / 60 / 60
    report += f'''\n{task}
    Date added: {date_added}
    Total time: {time_total} ~ {time_total_hours:.1f} hours'''
  return report

def menu_handler(user_id, text):
  users = db.read('users')
  state = users[user_id]['state']

  # STATE - start_task
  if state == 'start_task':
    task_name = text
    if task_name in users[user_id]['tasks'].keys():
      users[user_id]['active_task'] = {
          'name': task_name,
          'start_time':int(time.time())
          }
      db.write('users',users)
      tgbot.send_message(user_id, f'Started {task_name}', keyboard=get_main_menu(users, user_id))
      change_state(users, user_id, 'main_menu')
    else:
      tgbot.send_message(user_id, f'Task {task_name} does not exist', keyboard=get_main_menu(users, user_id))
      change_state(users, user_id, 'main_menu')

  # STATE - add_task
  elif state == 'add_task':
    task_name = text
    if task_name in users[user_id]['tasks'].keys():
      if users[user_id]['tasks'][task_name]['enabled']:
        tgbot.send_message(user_id, f'Task "{task_name}" already exists\nChoose another name\n/cancel')
      else:
        users[user_id]['tasks'][task_name]['enabled'] = True
        db.write('users',users)
        tgbot.send_message(user_id, f'Added task "{task_name}" again', keyboard=get_main_menu(users, user_id))
        change_state(users, user_id, 'main_menu')
    else: # adding task to db
      users[user_id]['tasks'].update(
          {task_name:{
            'enabled':True,
            'date_added':int(time.time()),
            'time_total':0,
            }}
          )
      db.write('users', users)
      tgbot.send_message(user_id, f'Added task "{task_name}"', keyboard=get_main_menu(users, user_id))
      change_state(users, user_id, 'main_menu')

  # STATE - remove_task
  elif state == 'remove_task':
    task_name = text
    if users[user_id]['active_task'] == task_name:
      users[user_id]['active_task'] = None
    if task_name in users[user_id]['tasks'].keys():
      users[user_id]['tasks'][task_name]['enabled'] = False
      db.write('users',users)
      tgbot.send_message(user_id, f'Removed task "{task_name}"', keyboard=get_main_menu(users, user_id))
    else:
      tgbot.send_message(user_id, f'Task "{task_name}" doesn\'t exist\n/cancel', keyboard=get_main_menu(users, user_id))
    change_state(users, user_id, 'main_menu')

  # STATE - set_timezone
  elif state == 'set_timezone':
    try:
      hour_offset = int(text)
      if hour_offset in range(-12, 15):
        users[user_id]['timezone'] = hour_offset
        db.write('users', users)
        if hour_offset >= 0:
          tz = f'UTC+{hour_offset}'
        else:
          tz = f'UTC{hour_offset}'
        tgbot.send_message(user_id, f'Timezone set to {tz}', keyboard=get_main_menu(users, user_id))
        change_state(users, user_id, 'main_menu')
      else:
        tgbot.send_message(user_id, 'Invalid UTC offset\nValid range (-12...+14)\n/cancel', keyboard=[])
    except ValueError:
      tgbot.send_message(user_id, 'UTC offset must be an integer\nValid range (-12...+14)\n/cancel', keyboard=[])

  # STATE - main_menu
  elif state == 'main_menu':
    button_name = text

    if button_name == constants.get_name('disable_menu'):
      disable_menu(user_id)

    elif button_name == constants.get_name('set_timezone'):
      tgbot.send_message(user_id, 'Send hour offset for UTC\nValid range (-12...+14)\n/cancel', keyboard=[])
      change_state(users, user_id, 'set_timezone')

    elif button_name == constants.get_name('start_task'):
      tasks = get_enabled_tasks(users, user_id)
      if tasks:
        keyboard = []
        for task in tasks:
          keyboard.append([task])
        tgbot.send_message(user_id, 'Choose a task to start\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'start_task')
      else:
        tgbot.send_message(user_id, "You don't have any tasks")

    elif button_name == constants.get_name('add_task'):
      tgbot.send_message(user_id, 'Name a task\n/cancel', keyboard = [])
      change_state(users, user_id, 'add_task')

    elif button_name == constants.get_name('remove_task'):
      tasks = get_enabled_tasks(users, user_id)
      if tasks:
        keyboard = []
        for task in tasks:
          keyboard.append([task])
        tgbot.send_message(user_id, 'Choose a task to remove\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'remove_task')
      else:
        tgbot.send_message(user_id, "You don't have any tasks")

    else: # Checking for "Stop {task}"
      stop_string = constants.get_name('stop')
      stop_string_len = len(stop_string)
      # removing active task
      if button_name[:stop_string_len] == stop_string:
        task_name = button_name[stop_string_len:]
        if users[user_id]['active_task']:
          if users[user_id]['active_task']['name'] == task_name:
            task_duration = stop_task(users, user_id, task_name)
            tgbot.send_message(user_id, f'Stopped {task_name}\nTime taken: {task_duration}', keyboard=get_main_menu(users, user_id))
        else:
          tgbot.send_message(user_id, f'Task "{task_name}" is not active', keyboard=get_main_menu(users, user_id))

    if button_name == constants.get_name('task_stats'):
      tgbot.send_message(user_id, get_task_stats(users ,user_id), keyboard=get_main_menu(users, user_id))
