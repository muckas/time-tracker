import logging
import os
import time
import datetime
from contextlib import suppress
import db
import tgbot
import constants
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import icalendar
import uuid

log = logging.getLogger('main')

temp_vars = {}

def check_temp_vars(user_id):
  if user_id not in temp_vars:
    temp_vars.update({user_id:constants.get_temp_vars()})

def timezoned(users, user_id, timestamp):
  delta = 60 * 60 * users[user_id]['timezone']
  return timestamp + delta

def send_calendar(user_id):
  date = datetime.datetime.now().date()
  file_path = os.path.join('db', 'data', user_id, f'tasks-calendar-{user_id}.ics')
  file_name = f'tasks-calendar-{date}.ics'
  success = tgbot.send_document(user_id, file_path, file_name)
  if not success:
    tgbot.send_message(user_id, 'Couldn\'t find your calendar :-(')

def update_timer(user_id, message, start_time, task_name):
  timer = int(time.time()) - start_time
  timer = datetime.timedelta(seconds=timer)
  text = f'{task_name}\n{timer}'
  with suppress(telegram.error.BadRequest):
    message.edit_text(text)
  # log.debug(f'Updated timer for user {user_id}: {text}')

def update_all_timers():
  for user_id in temp_vars:
    message = temp_vars[user_id]['timer_message']
    start_time = temp_vars[user_id]['timer_start']
    task_name = temp_vars[user_id]['task_name']
    if message and start_time and task_name:
      update_timer(user_id, message, start_time, task_name)

def get_new_timer(user_id):
  users = db.read('users')
  if users[user_id]['active_task']:
    message = tgbot.send_message(user_id, 'Timer')
    task_name = get_task_name(users, user_id, users[user_id]['active_task']['id'])
    start_time = users[user_id]['active_task']['start_time']
    temp_vars[user_id].update({'timer_message':message, 'timer_start':start_time, 'desired_task':task_name})
    update_timer(user_id, message, start_time, task_name)
  else:
    tgbot.send_message(user_id, 'No task is active')

def get_main_menu(users, user_id):
  active_task = users[user_id]['active_task']
  if active_task:
    task_name = get_task_name(users, user_id, active_task['id'])
    start_task_button = f'{constants.get_name("stop")}{task_name}'
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

def get_options_keyboard(options, columns=2):
  keyboard = []
  for index in range(0, len(options), columns):
    row = []
    for offset in range(columns):
      with suppress(IndexError):
        row.append(options[index+offset])
    keyboard.append(row)
  return keyboard

def enable_menu(users, user_id):
  change_state(users, user_id, 'main_menu')
  tgbot.send_message(user_id, 'Main menu', keyboard=get_main_menu(users, user_id))

def disable_menu(user_id):
  tgbot.send_message(user_id, 'Menu disabled', keyboard=[])

def change_state(users, user_id, new_state):
  temp_vars[user_id]['state'] = new_state
  username = users[user_id]['username']
  log.debug(f'New state "{new_state}" for user @{username}({user_id})')

def get_task_id(users, user_id, task_name):
  for task_id in users[user_id]['tasks']:
    if users[user_id]['tasks'][task_id]['name'] == task_name:
      return task_id
  return None

def get_task_name(users, user_id, task_id):
  return users[user_id]['tasks'][task_id]['name']

def get_enabled_tasks(users, user_id):
  tasks = users[user_id]['tasks']
  enabled_tasks = []
  for task_id in tasks:
    if tasks[task_id]['enabled']:
      enabled_tasks.append(task_id)
  return enabled_tasks

def get_enabled_tasks_names(users, user_id):
  tasks = users[user_id]['tasks']
  enabled_tasks = []
  for task_id in tasks:
    if tasks[task_id]['enabled']:
      enabled_tasks.append(tasks[task_id]['name'])
  return enabled_tasks

def get_all_tasks(users, user_id):
  return users[user_id]['tasks'].keys()

def get_all_tasks_names(users, user_id):
  tasks = users[user_id]['tasks']
  all_tasks = []
  for task_id in tasks:
    all_tasks.append(tasks[task_id]['name'])
  return all_tasks

def add_task(users, user_id, task_name, enabled=True):
  if task_name in get_all_tasks_names(users, user_id):
    task_id = get_task_id(users, user_id, task_name)
    if users[user_id]['tasks'][task_id]['enabled']:
      return None
    else:
      users[user_id]['tasks'][task_id]['enabled'] = True
      db.write('users', users)
      return f'Enabled task "{task_name}"'
  else: # adding task to db
    new_task_id = str(uuid.uuid4())
    users[user_id]['tasks'].update(
        {new_task_id:constants.get_default_task(task_name)}
        )
    users[user_id]['tasks'][new_task_id]['enabled'] = enabled
    db.write('users', users)
    return f'Added task "{task_name}"'

def stop_task(users, user_id, task_id, time_text):
  task_name = get_task_name(users, user_id, task_id)
  temp_vars[user_id].update({'timer_message':None, 'timer_start':None, 'task_name':None})
  task_start_time = users[user_id]['active_task']['start_time']
  # Retroactive task stopping
  if time_text == constants.get_name('now'):
    task_end_time = int(time.time())
  else:
    time_interval = convert_interval_to_seconds(time_text)
    if time_interval:
      if int(time.time()) - time_interval <= task_start_time:
        users[user_id]['active_task'] = None
        db.write('users',users)
        return 'None'
      else:
        task_end_time = int(time.time()) - time_interval
    else:
      return None
  write_task_to_diary(users, user_id, task_id, task_start_time, task_end_time)
  users[user_id]['last_task_end_time'] = task_end_time
  task_duration_sec = task_end_time - task_start_time
  task_duration = datetime.timedelta(seconds=task_duration_sec)
  users[user_id]['active_task'] = None
  users[user_id]['tasks'][task_id]['time_total'] += task_duration_sec
  db.write('users',users)
  return task_duration

def write_task_to_diary(users, user_id, task_id, start_time, end_time):
  timezone = users[user_id]['timezone']
  write_to_task_list(user_id, task_id, timezone, start_time, end_time)
  write_to_ical(users, user_id, task_id, start_time, end_time)
  tzoffset = datetime.timezone(datetime.timedelta(hours=timezone))
  tz_start_time = timezoned(users, user_id, start_time)
  tz_end_time = timezoned(users, user_id, end_time)
  start_date = datetime.datetime.utcfromtimestamp(tz_start_time)
  end_date = datetime.datetime.utcfromtimestamp(tz_end_time)
  one_second = datetime.timedelta(seconds=1)
  while True:
    if start_date.date() == end_date.date():
      update_diary_day(users, user_id, task_id, start_date.timestamp(), end_date.timestamp(), timezone)
      break
    temp_end_date = start_date.replace(hour=23, minute=59, second=59)
    update_diary_day(users, user_id, task_id, start_date.timestamp(), temp_end_date.timestamp(), timezone)
    start_date = temp_end_date + one_second

def write_to_task_list(user_id, task_id, timezone, start_time, end_time):
  task_list_filename = f'tasks-{user_id}'
  task_list_path = os.path.join('data', user_id, task_list_filename)
  task_list = db.read(task_list_path)
  if not task_list: task_list = []
  task_list.append(constants.get_default_list_task(task_id, timezone, start_time, end_time))
  db.write(task_list_path, task_list)

def write_to_ical(users, user_id, task_id, start_time, end_time):
  calendar_name = f'tasks-calendar-{user_id}.ics'
  calendar_path = os.path.join('db', 'data', user_id, calendar_name)
  timezone = users[user_id]['timezone']
  if os.path.isfile(calendar_path):
    log.debug(f'Reading from {calendar_path}')
    cal = icalendar.Calendar.from_ical(open(calendar_path, 'rb').read())
  else:
    log.debug(f'Making new calendar')
    cal = constants.get_new_calendar('Time-Tracker: Tasks', timezone)
  task_duration = end_time - start_time
  if task_duration < 60 * 60:
    task_duration /= 60
    task_duration = f' {int(task_duration)}m'
  else:
    task_duration /= 60 * 60
    task_duration = f' {task_duration:.1f}h'
  summary = users[user_id]['tasks'][task_id]['name'] + task_duration
  tzoffset_hours = timezone
  tzoffset_sec = tzoffset_hours * 60 * 60
  dtstart = datetime.datetime.utcfromtimestamp(start_time + tzoffset_sec)
  dtend = datetime.datetime.utcfromtimestamp(end_time + tzoffset_sec)
  event = icalendar.Event()
  event_id = uuid.uuid4()
  event.add('UID', event_id)
  event.add('summary', summary)
  event.add('tzoffset', tzoffset_hours)
  event.add('dtstart', dtstart)
  event.add('dtend', dtend)
  cal.add_component(event)
  log.debug(f'Added event {event_id} to calendar')
  with open(calendar_path, 'wb') as f:
    log.debug(f'Writing to {calendar_path}')
    f.write(cal.to_ical())

def update_diary_day(users, user_id, task_id, tz_start_time, tz_end_time, timezone):
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
    diary['tasks_total'][task_id] += tz_time_total
  except KeyError:
    diary['tasks_total'][task_id] = tz_time_total
  try:
    diary['days'][day_number]['tasks_total'][task_id] += tz_time_total
  except KeyError:
    diary['days'][day_number]['tasks_total'][task_id] = tz_time_total

  diary['days'][day_number]['tasks'].append(
      {
        'type':'task',
        'id':task_id,
        'start_time':tz_start_time,
        'end_time':tz_end_time,
        'total_time':tz_time_total
        }
      )
  db.write(diary_path, diary)

def get_task_stats(users, user_id, option=None):
  stats_delta = temp_vars[user_id]['stats_delta']
  stats_type = users[user_id]['stats_type']
  timezone = users[user_id]['timezone']
  tzdelta = datetime.timezone(datetime.timedelta(hours=timezone))
  if option == 'alltime':
    stats_type = 'alltime'
    stats_delta = 0
    temp_vars[user_id]['stats_delta'] = 0
    users[user_id]['stats_type'] = stats_type
    db.write('users', users)
  elif option == 'detailed':
    stats_type = 'detailed'
    stats_delta = 0
    temp_vars[user_id]['stats_delta'] = 0
    users[user_id]['stats_type'] = stats_type
    db.write('users', users)
  elif option == 'month':
    stats_type = 'month'
    stats_delta = 0
    temp_vars[user_id]['stats_delta'] = 0
    users[user_id]['stats_type'] = stats_type
    db.write('users', users)
  elif option == 'day':
    stats_type = 'day'
    stats_delta = 0
    temp_vars[user_id]['stats_delta'] = 0
    users[user_id]['stats_type'] = stats_type
    db.write('users', users)
  elif option == 'left':
    stats_delta += 1
    temp_vars[user_id]['stats_delta'] = stats_delta
  elif option == 'right' and stats_delta > 0:
    stats_delta -= 1
    temp_vars[user_id]['stats_delta'] = stats_delta

  if stats_type == 'detailed':
    tasks = get_all_tasks(users, user_id)
    report = 'Detailed statistics:\n--------------------'
    for task_id in tasks:
      task_info = users[user_id]['tasks'][task_id]
      date_added = timezoned(users, user_id, task_info['date_added'])
      date_added = datetime.datetime.utcfromtimestamp(date_added)
      time_total = datetime.timedelta(seconds=task_info['time_total'])
      time_total_hours = task_info['time_total'] / 60 / 60
      task_status = ''
      if not task_info['enabled']: task_status = '(disabled)'
      report += f'''\n{get_task_name(users, user_id, task_id)}{task_status}
      Date added: {date_added}
      Total time: {time_total} ~ {time_total_hours:.1f} hours'''
    keyboard = [
        [InlineKeyboardButton('Day', callback_data='task_stats:day')],
        [InlineKeyboardButton('Month', callback_data='task_stats:month')],
        [InlineKeyboardButton('All time', callback_data='task_stats:alltime')],
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return report, reply_markup

  elif stats_type == 'alltime':
    tasks = get_enabled_tasks(users, user_id)
    report = 'All time statistics:\n--------------------'
    for task_id in tasks:
      task_info = users[user_id]['tasks'][task_id]
      time_total = datetime.timedelta(seconds=task_info['time_total'])
      time_total_hours = task_info['time_total'] / 60 / 60
      report += f'\n{get_task_name(users, user_id, task_id)}: {time_total} ~ {time_total_hours:.1f} hours'
    keyboard = [
        [InlineKeyboardButton('Day', callback_data='task_stats:day')],
        [InlineKeyboardButton('Month', callback_data='task_stats:month')],
        [InlineKeyboardButton('Detailed', callback_data='task_stats:detailed')],
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return report, reply_markup

  elif stats_type == 'month':
    timedelta = datetime.timedelta(days=30 * stats_delta)
    date = datetime.datetime.now(tzdelta) - timedelta
    filename = f'{date.year}-{date.month}-{user_id}'
    report = f'Month statistics: {date.year}-{date.month}\n--------------------'
    diary = db.read(os.path.join('data', user_id, filename))
    if diary:
      for task_id in diary['tasks_total']:
        task_time = diary['tasks_total'][task_id]
        time_total = datetime.timedelta(seconds=task_time)
        time_total_hours = task_time / 60 / 60
        report += f'\n{get_task_name(users, user_id, task_id)}: {time_total} ~ {time_total_hours:.1f} hours'
    else:
      report += f'\nNo data for {date.year}-{date.month}'
    keyboard = [
        [InlineKeyboardButton('Day', callback_data='task_stats:day')],
        [InlineKeyboardButton('All time', callback_data='task_stats:alltime')],
        [InlineKeyboardButton('Detailed', callback_data='task_stats:detailed')],
        [
          InlineKeyboardButton('<', callback_data='task_stats:left'),
          InlineKeyboardButton('>', callback_data='task_stats:right'),
          ]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return report, reply_markup
  elif stats_type == 'day':
    timedelta = datetime.timedelta(days=stats_delta)
    date = datetime.datetime.now(tzdelta) - timedelta
    filename = f'{date.year}-{date.month}-{user_id}'
    report = f'Day statistics: {date.year}-{date.month}-{date.day}\n--------------------'
    diary = db.read(os.path.join('data', user_id, filename))
    day = str(date.day)
    if diary and day in diary['days'].keys():
      for task_id in diary['days'][day]['tasks_total']:
        task_time = diary['days'][day]['tasks_total'][task_id]
        time_total = datetime.timedelta(seconds=task_time)
        time_total_hours = task_time / 60 / 60
        report += f'\n{get_task_name(users, user_id, task_id)}: {time_total} ~ {time_total_hours:.1f} hours'
    else:
      report += f'\nNo data for {date.year}-{date.month}-{date.day}'
    keyboard = [
        [InlineKeyboardButton('Month', callback_data='task_stats:month')],
        [InlineKeyboardButton('All time', callback_data='task_stats:alltime')],
        [InlineKeyboardButton('Detailed', callback_data='task_stats:detailed')],
        [
          InlineKeyboardButton('<', callback_data='task_stats:left'),
          InlineKeyboardButton('>', callback_data='task_stats:right'),
          ]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return report, reply_markup
  else:
    return 'Wrong query data', None

def convert_interval_to_seconds(text):
  if text[:1] == '-': text = text[1:]
  with suppress(ValueError):
    time_interval = int(text[:-1])
    time_type = text[-1:]
    if time_type == 's':
      return time_interval
    if time_type == 'm':
      return time_interval * 60
    if time_type == 'h':
      return time_interval * 60 * 60
    if time_type == 'd':
      return time_interval * 60 * 60 * 24
  return None

def menu_handler(user_id, text):
  users = db.read('users')
  state = temp_vars[user_id]['state']

  # STATE - start_task
  if state == 'start_task':
    # Retroactive task starting
    if text == constants.get_name('now'):
      start_time = int(time.time())
    else:
      time_interval = convert_interval_to_seconds(text)
      if time_interval:
        start_time = max(int(time.time()) - time_interval, users[user_id]['last_task_end_time'])
      else:
        tgbot.send_message(user_id, f'Incorrect time "{text}"', keyboard=get_main_menu(users, user_id))
        change_state(users, user_id, 'main_menu')
        return

    task_name = temp_vars[user_id]['task_name']
    task_id = get_task_id(users, user_id, task_name)
    if task_name not in get_all_tasks_names(users, user_id):
      add_task(users, user_id, task_name, enabled=False)
      tgbot.send_message(user_id, f'Added custom task {task_name}')
    users[user_id]['active_task'] = {
        'id': task_id,
        'start_time':start_time
        }
    db.write('users',users)
    tgbot.send_message(user_id, f'Started {task_name}', keyboard=get_main_menu(users, user_id))
    change_state(users, user_id, 'main_menu')
    message = tgbot.send_message(user_id, f'Timer')
    update_timer(user_id, message, start_time, task_name)
    temp_vars[user_id].update({'timer_message':message, 'timer_start':start_time})

  # STATE - start_task_time
  if state == 'start_task_time':
    task_name = text
    temp_vars[user_id].update({'task_name':task_name})
    keyboard = [[constants.get_name('now')]] + get_options_keyboard(constants.get_time_presets(), columns=3)
    tgbot.send_message(user_id, f'When to start {task_name}?\n/cancel', keyboard=keyboard)
    change_state(users, user_id, 'start_task')

  if state == 'stop_task':
    time_interval = text
    if users[user_id]['active_task']:
      task_id = users[user_id]['active_task']['id']
      task_name = get_task_name(users, user_id, task_id)
      task_duration = stop_task(users, user_id, task_id, time_interval)
      if task_duration != None:
        tgbot.send_message(user_id, f'Stopped {task_name}\nTime taken: {task_duration}', keyboard=get_main_menu(users, user_id))
        change_state(users, user_id, 'main_menu')
      else:
        tgbot.send_message(user_id, f'Incorrect time "{text}"', keyboard=get_main_menu(users, user_id))
        change_state(users, user_id, 'main_menu')
    else:
      tgbot.send_message(user_id, f'No task is active', keyboard=get_main_menu(users, user_id))

  # STATE - add_task
  elif state == 'add_task':
    task_name = text
    result = add_task(users, user_id, task_name)
    if result:
      tgbot.send_message(user_id, result, keyboard=get_main_menu(users, user_id))
      change_state(users, user_id, 'main_menu')
    else:
      tgbot.send_message(user_id, f'Task "{task_name}" already exists\nChoose another name\n/cancel')

  # STATE - remove_task
  elif state == 'remove_task':
    task_name = text
    task_id = get_task_id(users, user_id, task_name)
    if task_id != None:
      users[user_id]['tasks'][task_id]['enabled'] = False
      db.write('users',users)
      tgbot.send_message(user_id, f'Disabled task "{task_name}"', keyboard=get_main_menu(users, user_id))
    else:
      tgbot.send_message(user_id, f'Task "{task_name}" does not exist', keyboard=get_main_menu(users, user_id))
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
      tasks = get_enabled_tasks_names(users, user_id)
      if tasks:
        keyboard = get_options_keyboard(tasks, columns=3)
        tgbot.send_message(user_id, 'Choose a task to start\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'start_task_time')
      else:
        tgbot.send_message(user_id, "You don't have any tasks")

    elif button_name == constants.get_name('add_task'):
      tgbot.send_message(user_id, 'Name a task\n/cancel', keyboard = [])
      change_state(users, user_id, 'add_task')

    elif button_name == constants.get_name('remove_task'):
      tasks = get_enabled_tasks_names(users, user_id)
      if tasks:
        keyboard = get_options_keyboard(tasks, columns=3)
        tgbot.send_message(user_id, 'Choose a task to remove\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'remove_task')
      else:
        tgbot.send_message(user_id, "You don't have any tasks")

    elif button_name == constants.get_name('task_stats'):
      temp_vars[user_id]['stats_delta'] = 0
      report, reply_markup = get_task_stats(users ,user_id, users[user_id]['stats_type'])
      tgbot.send_message(user_id, report, reply_markup=reply_markup)

    else: # Checking for "Stop {task}"
      stop_string = constants.get_name('stop')
      stop_string_len = len(stop_string)
      # removing active task
      if button_name[:stop_string_len] == stop_string: # stop_task
        task_id = users[user_id]['active_task']['id']
        task_name = get_task_name(users, user_id, task_id)
        keyboard = [[constants.get_name('now')]] + get_options_keyboard(constants.get_time_presets(), columns=3)
        tgbot.send_message(user_id, f'When to stop {task_name}?\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'stop_task')
      else:
        tgbot.send_message(user_id, 'Error, try again')
        enable_menu(users, user_id)
