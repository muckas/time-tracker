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
import hashlib

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

def send_links(users, user_id):
  web_key = users[user_id]['web_key']
  params = db.read('params')
  web_path = params['web_path']
  if web_key:
    text = f'''Tasks calendar:
{web_path}{web_key}/tasks.ics
Context calendar:
{web_path}{web_key}/context.ics
Places calendar:
{web_path}{web_key}/places.ics
'''
    tgbot.send_message(user_id, text)
  else:
    generate_new_key(users, user_id, '')

def generate_new_key(users, user_id, string):
  encoded_string = f'{user_id}{string}'.encode()
  hash_obj = hashlib.md5(encoded_string)
  hash_hex = hash_obj.hexdigest()
  users[user_id]['web_key'] = hash_hex
  db.write('users', users)
  log.debug(f'Generated new key for user {user_id}')
  send_links(users, user_id)

def update_timer(user_id):
  task_name = ''
  task_description = ''
  task_start = ''
  task_timer = ''
  context_name = ''
  context_description = ''
  context_start = ''
  context_timer = ''
  message = temp_vars[user_id]['timer_message']
  if temp_vars[user_id]['task_name'] and temp_vars[user_id]['task_start']:
    task_name = '\n' + temp_vars[user_id]['task_name']
    task_description = '\n' + temp_vars[user_id]['task_description']
    task_start = temp_vars[user_id]['task_start']
    task_timer = int(time.time()) - task_start
    task_timer = datetime.timedelta(seconds=task_timer)
  if temp_vars[user_id]['context_name'] and temp_vars[user_id]['context_start']:
    context_name = '\n' + temp_vars[user_id]['context_name']
    context_description = '\n' + temp_vars[user_id]['context_description']
    context_start = temp_vars[user_id]['context_start']
    context_timer = int(time.time()) - context_start
    context_timer = datetime.timedelta(seconds=context_timer)
  emoji = ''
  if temp_vars[user_id]['task_start']:
    emoji += '\U0001F534'
  if temp_vars[user_id]['context_start']:
    emoji += '\U00002b55'
  text = f'{emoji}\n'
  text += f'{task_timer}{task_name}{task_description}'
  if task_start:
    text += '\n---------------\n'
  text += f'{context_timer}{context_name}{context_description}'
  with suppress(telegram.error.BadRequest):
    message.edit_text(text)
  # log.debug(f'Updated timer for user {user_id}: {text}')

def update_all_timers():
  for user_id in temp_vars:
    message = temp_vars[user_id]['timer_message']
    task_name = temp_vars[user_id]['task_name']
    task_start = temp_vars[user_id]['task_start']
    context_name = temp_vars[user_id]['context_name']
    context_start = temp_vars[user_id]['context_start']
    if message and ((task_name and task_start) or (context_name and context_start)):
      update_timer(user_id)

def get_new_timer(user_id, notify=True):
  users = db.read('users')
  active_task = users[user_id]['active_task']
  active_context = users[user_id]['active_context']
  if active_task or active_context:
    if active_task:
      task_name = get_name(users, user_id, 'task', active_task['id'])
      task_description = active_task['description']
      task_start = active_task['start_time']
      temp_vars[user_id].update({
        'task_start':task_start,
        'task_name':task_name,
        'task_description':task_description
        })
    if active_context:
      context_name = get_name(users, user_id, 'task', active_context['id'])
      context_description = active_context['description']
      context_start = active_context['start_time']
      temp_vars[user_id].update({
        'context_start':context_start,
        'context_name':context_name,
        'context_description':context_description
        })
    message = tgbot.send_message(user_id, 'Timer')
    temp_vars[user_id].update({'timer_message':message})
    update_timer(user_id)
  elif notify:
    tgbot.send_message(user_id, 'No task is active')

def get_main_menu(users, user_id):
  menu_state = temp_vars[user_id]['menu_state']
  active_task = users[user_id]['active_task']
  active_place = users[user_id]['active_place']
  active_context = users[user_id]['active_context']
  if menu_state == 'menu_main':
    if active_task:
      task_name = get_name(users, user_id, 'task', active_task['id'])
      start_task_button = f'{constants.get_name("stop")}{task_name}'
    else:
      start_task_button = constants.get_name('start_task')
    if active_place:
      place_name = get_name(users, user_id, 'place', active_place['id'])
      change_place_button = f'{constants.get_name("change_place")}{place_name}'
    else:
      change_place_button = constants.get_name('change_place') + 'None'
    if active_context:
      context_name = get_name(users, user_id, 'tasks', active_context['id'])
      change_context_button = f'{constants.get_name("change_context")}{context_name}'
    else:
      change_context_button = constants.get_name('no_context')
    keyboard = [
        [
          start_task_button,
        ],
        [
          change_place_button,
          change_context_button,
        ],
        [
          constants.get_name('menu_ext'),
          constants.get_name('menu_stats'),
          constants.get_name('menu_edit'),
          constants.get_name('menu_settings')
        ],
      ]
    if users[user_id]['timezone'] == None:
      keyboard[0] = [constants.get_name('set_timezone')]

  elif menu_state == 'menu_ext':
    keyboard = [
        [
          constants.get_name('task_description'),
        ],
        [
          constants.get_name('context_description'),
        ],
        [
          constants.get_name('menu_main'),
          constants.get_name('menu_stats'),
          constants.get_name('menu_edit'),
          constants.get_name('menu_settings'),
        ],
      ]

  elif menu_state == 'menu_stats':
    keyboard = [
        [
          constants.get_name('entry_stats'),
        ],
        [
          constants.get_name('entry_info'),
        ],
        [
          constants.get_name('menu_main'),
          constants.get_name('menu_stats'),
          constants.get_name('menu_edit'),
          constants.get_name('menu_settings'),
        ],
      ]

  elif menu_state == 'menu_settings':
    keyboard = [
        [constants.get_name('set_timezone')],
        [
          constants.get_name('add_tag'),
          constants.get_name('enable_tag'),
          constants.get_name('disable_tag'),
        ],
        [
          constants.get_name('menu_main'),
          constants.get_name('menu_stats'),
          constants.get_name('menu_edit'),
          constants.get_name('disable_menu'),
        ],
      ]

  elif menu_state == 'menu_edit':
    keyboard = [
        [
          constants.get_name('menu_edit_tasks'),
          constants.get_name('menu_edit_places'),
        ],
        [
          constants.get_name('menu_edit_tags'),
        ],
        [
          constants.get_name('menu_main'),
          constants.get_name('menu_stats'),
          constants.get_name('menu_edit'),
          constants.get_name('menu_settings'),
        ],
      ]

  elif menu_state == 'menu_edit_tasks':
    keyboard = [
        [
          constants.get_name('add_task'),
          constants.get_name('task_tags'),
        ],
        [
          constants.get_name('enable_task'),
          constants.get_name('remove_task'),
        ],
        [
          constants.get_name('menu_main'),
          constants.get_name('menu_stats'),
          constants.get_name('menu_edit'),
          constants.get_name('menu_settings'),
        ],
      ]

  elif menu_state == 'menu_edit_places':
    keyboard = [
        [
          constants.get_name('add_place'),
          constants.get_name('place_tags'),
        ],
        [
          constants.get_name('enable_place'),
          constants.get_name('disable_place'),
        ],
        [
          constants.get_name('menu_main'),
          constants.get_name('menu_stats'),
          constants.get_name('menu_edit'),
          constants.get_name('menu_settings'),
        ],
      ]

  elif menu_state == 'menu_edit_tags':
    keyboard = [
        [
          constants.get_name('add_tag'),
        ],
        [
          constants.get_name('enable_tag'),
          constants.get_name('disable_tag'),
        ],
        [
          constants.get_name('menu_main'),
          constants.get_name('menu_stats'),
          constants.get_name('menu_edit'),
          constants.get_name('menu_settings'),
        ],
      ]
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

def get_inline_options_keyboard(options_dict, columns=2):
  keyboard = []
  for index in range(0, len(options_dict), columns):
    row = []
    for offset in range(columns):
      with suppress(IndexError):
        option_key = list(options_dict.keys())[index + offset]
        row.append(InlineKeyboardButton(option_key, callback_data=options_dict[option_key]))
    keyboard.append(row)
  return keyboard

def enable_menu(users, user_id):
  change_state(users, user_id, 'main_menu')
  tgbot.send_message(user_id, 'Menu enabled', keyboard=get_main_menu(users, user_id))

def disable_menu(user_id):
  tgbot.send_message(user_id, 'Menu disabled', keyboard=[])

def change_state(users, user_id, new_state):
  temp_vars[user_id]['state'] = new_state
  username = users[user_id]['username']
  log.debug(f'New state "{new_state}" for user @{username}({user_id})')

def change_menu_state(users, user_id, new_state):
  temp_vars[user_id]['menu_state'] = new_state
  username = users[user_id]['username']
  log.debug(f'New menu state "{new_state}" for user @{username}({user_id})')

def get_id(users, user_id, info_type, info_name):
  if info_type in ('task', 'tasks',):
    entry_list = users[user_id]['tasks']
  elif info_type in ('place', 'places',):
    entry_list = users[user_id]['places']
  elif info_type in ('all',):
    entry_list = dict(users[user_id]['tasks'], **users[user_id]['places'])
  for entry_id in entry_list:
    if entry_list[entry_id]['name'] == info_name:
      return entry_id
  return None

def get_name(users, user_id, info_type, info_id):
  if info_type in ('task', 'tasks',):
    entry_list = users[user_id]['tasks']
  elif info_type in ('place', 'places',):
    entry_list = users[user_id]['places']
  elif info_type in ('all',):
    entry_list = dict(users[user_id]['tasks'], **users[user_id]['places'])
  if info_id in entry_list.keys():
    return entry_list[info_id]['name']
  else:
    return None

def get_enabled(users, user_id, info_type):
  if info_type in ('task', 'tasks',):
    entry_list = users[user_id]['tasks']
  elif info_type in ('place', 'places',):
    entry_list = users[user_id]['places']
  enabled_entries = []
  for entry_id in entry_list:
    if entry_list[entry_id]['enabled']:
      enabled_entries.append(entry_id)
  return enabled_entries

def get_disabled(users, user_id, info_type):
  if info_type in ('task', 'tasks',):
    entry_list = users[user_id]['tasks']
  elif info_type in ('place', 'places',):
    entry_list = users[user_id]['places']
  disabled_entries = []
  for entry_id in entry_list:
    if not entry_list[entry_id]['enabled']:
      disabled_entries.append(entry_id)
  return disabled_entries

def get_enabled_names(users, user_id, info_type):
  if info_type in ('task', 'tasks',):
    entry_list = users[user_id]['tasks']
  elif info_type in ('place', 'places',):
    entry_list = users[user_id]['places']
  enabled_entries = []
  for entry_id in entry_list:
    if entry_list[entry_id]['enabled']:
      enabled_entries.append(entry_list[entry_id]['name'])
  return enabled_entries

def get_disabled_names(users, user_id, info_type):
  if info_type in ('task', 'tasks',):
    entry_list = users[user_id]['tasks']
  elif info_type in ('place', 'places',):
    entry_list = users[user_id]['places']
  disabled_entries = []
  for entry_id in entry_list:
    if not entry_list[entry_id]['enabled']:
      disabled_entries.append(entry_list[entry_id]['name'])
  return disabled_entries

def get_all(users, user_id, info_type):
  if info_type in ('task', 'tasks',):
    entry_list = users[user_id]['tasks']
  elif info_type in ('place', 'places',):
    entry_list = users[user_id]['places']
  elif info_type in ('all',):
    entry_list = dict(users[user_id]['tasks'], **users[user_id]['places'])
  return entry_list.keys()

def get_all_names(users, user_id, info_type):
  if info_type in ('task', 'tasks',):
    entry_list = users[user_id]['tasks']
  elif info_type in ('place', 'places',):
    entry_list = users[user_id]['places']
  elif info_type in ('all',):
    entry_list = dict(users[user_id]['tasks'], **users[user_id]['places'])
  all_entries = []
  for entry_id in entry_list:
    all_entries.append(entry_list[entry_id]['name'])
  return all_entries

def get_entry_ids_with_tags(users, user_id, info_type, tags=[]):
  if info_type in ('task', 'tasks',):
    entry_list = users[user_id]['tasks']
  elif info_type in ('place', 'places',):
    entry_list = users[user_id]['places']
  elif info_type in ('all',):
    entry_list = dict(users[user_id]['tasks'], **users[user_id]['places'])
  tag_ids = []
  for tag_name in tags:
    tag_ids.append(get_tag_id(users, user_id, tag_name))
  entries = []
  for entry_id in entry_list:
    entry_tags = get_entry_tags(users, user_id, entry_id)
    if len(set(entry_tags).intersection(tag_ids)) > 0:
      entries.append(entry_id)
  return entries

def get_entry_names_with_tags(users, user_id, info_type, tags=[]):
  entries = get_entry_ids_with_tags(users, user_id, info_type, tags)
  entry_names = []
  for entry_id in entries:
    entry_names.append(get_name(users, user_id, info_type, entry_id))
  return entry_names

def get_entry_tags(users, user_id, entry_id):
  if entry_id in users[user_id]['tasks'].keys():
    return users[user_id]['tasks'][entry_id]['tags']
  elif entry_id in users[user_id]['places'].keys():
    return users[user_id]['places'][entry_id]['tags']
  else:
    return None

def get_entry_tags_names(users, user_id, entry_id):
  tags_list = get_entry_tags(users, user_id, entry_id)
  tags_names = []
  for tag_id in tags_list:
    tags_names.append(get_tag_name(users, user_id, tag_id))
  return tags_names

def get_all_tags(users, user_id, enabled_only=False, disabled_only=False):
  tags_list = users[user_id]['tags']
  if enabled_only:
    for tag_id in tags_list.copy():
      if tags_list[tag_id]['enabled'] == False:
        tags_list.pop(tag_id)
  elif disabled_only:
    for tag_id in tags_list.copy():
      if tags_list[tag_id]['enabled'] == True:
        tags_list.pop(tag_id)
  return tags_list

def get_all_tags_by_function(users, user_id, function, enabled_only=False, disabled_only=False):
  tags_list_all = get_all_tags(users, user_id, enabled_only, disabled_only)
  tag_list_with_function = []
  for tag_id in tags_list_all:
    if function in users[user_id]['tags'][tag_id]['functions']:
      tag_list_with_function.append(tag_id)
  return tag_list_with_function

def get_all_tags_names(users, user_id, enabled_only=False, disabled_only=False):
  tags_list = get_all_tags(users, user_id, enabled_only, disabled_only)
  names_list = []
  for tag_id in tags_list:
    names_list.append(tags_list[tag_id]['name'])
  return names_list

def get_tag_name(users, user_id, tag_id):
  tags_list = users[user_id]['tags']
  if tag_id in tags_list.keys():
    return tags_list[tag_id]['name']

def get_tag_id(users, user_id, name):
  tags_list = users[user_id]['tags']
  for tag_id in tags_list:
    if tags_list[tag_id]['name'] == name:
      return tag_id
  return None

def add_task(users, user_id, task_name, enabled=True):
  if task_name in get_all_names(users, user_id, 'task'):
    task_id = get_id(users, user_id, 'task', task_name)
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

def stop_task(users, user_id, task_id, time_text, context=False):
  task_name = get_name(users, user_id, 'task', task_id)
  if context:
    temp_vars[user_id].update({'context_start':None, 'context_name':None, 'context_description':None})
    task_start_time = users[user_id]['active_context']['start_time']
    task_description = users[user_id]['active_context']['description']
  else:
    temp_vars[user_id].update({'task_start':None, 'task_name':None, 'task_description':None})
    task_start_time = users[user_id]['active_task']['start_time']
    task_description = users[user_id]['active_task']['description']
  # Retroactive task stopping
  if time_text == constants.get_name('now'):
    task_end_time = int(time.time())
  else:
    time_interval = convert_interval_to_seconds(time_text)
    if time_interval:
      if int(time.time()) - time_interval <= task_start_time:
        if context:
          users[user_id]['active_context'] = None
        else:
          users[user_id]['active_task'] = None
        db.write('users',users)
        return 'None'
      else:
        task_end_time = int(time.time()) - time_interval
    else:
      return None
  timezone = users[user_id]['timezone']
  write_task_description(users, user_id, task_id, task_description, task_start_time, task_end_time)
  write_task_to_diary(users, user_id, task_id, task_description, task_start_time, task_end_time, timezone, context=context)
  # Updating task info in users.json
  if context:
    users[user_id]['last_context_end_time'] = task_end_time
    users[user_id]['active_context'] = None
  else:
    users[user_id]['last_task_end_time'] = task_end_time
    users[user_id]['active_task'] = None
  task_duration_sec = task_end_time - task_start_time
  task_duration = datetime.timedelta(seconds=task_duration_sec)
  users[user_id]['tasks'][task_id]['last_active'] = task_end_time
  users[user_id]['tasks'][task_id]['time_total'] += task_duration_sec
  db.write('users',users)
  return task_duration

def write_task_description(users, user_id, task_id, description_name, task_start_time, task_end_time):
  if description_name:
    description_id = get_description_id(users, user_id, task_id, description_name)
    if not description_id:
      description_id = str(uuid.uuid4())
      users[user_id]['tasks'][task_id]['descriptions'].update(
          {description_id:constants.get_default_description(description_name)}
          )
    task_total_time = task_end_time - task_start_time
    users[user_id]['tasks'][task_id]['descriptions'][description_id]['time_total'] += int(task_total_time)
    users[user_id]['tasks'][task_id]['descriptions'][description_id]['last_active'] = int(time.time())
    db.write('users', users)

def write_task_to_diary(users, user_id, task_id, task_description,
                       start_time, end_time, timezone, context=False, totals_obj=None
                       ):
  if not totals_obj:
    event_id = str(uuid.uuid4())
    write_to_task_list(user_id, event_id, task_id, task_description, timezone, start_time, end_time, context=context)
    write_to_task_ical(users, user_id, event_id, task_id, task_description, start_time, end_time, context=context)
  tzoffset = datetime.timezone(datetime.timedelta(hours=timezone))
  tz_start_time = timezoned(users, user_id, start_time)
  tz_end_time = timezoned(users, user_id, end_time)
  start_date = datetime.datetime.utcfromtimestamp(tz_start_time)
  end_date = datetime.datetime.utcfromtimestamp(tz_end_time)
  one_second = datetime.timedelta(seconds=1)
  while True:
    if start_date.date() == end_date.date():
      update_task_totals(users, user_id, task_id, start_date.timestamp(), end_date.timestamp(), totals_obj)
      break
    temp_end_date = start_date.replace(hour=23, minute=59, second=59)
    update_task_totals(users, user_id, task_id, start_date.timestamp(), temp_end_date.timestamp(), totals_obj)
    start_date = temp_end_date + one_second

def write_to_task_list(user_id, event_id, task_id, task_description,
                      timezone, start_time, end_time, context=True
                      ):
  if context:
    task_list_filename = f'context-{user_id}'
  else:
    task_list_filename = f'tasks-{user_id}'
  task_list_path = os.path.join('data', user_id, task_list_filename)
  task_list = db.read(task_list_path)
  if not task_list: task_list = {}
  task_list[event_id] = constants.get_default_list_task(task_id, task_description, timezone, start_time, end_time)
  db.write(task_list_path, task_list)

def write_to_task_ical(users, user_id, event_id, task_id, task_description,
                      start_time, end_time, context=False, ical_obj=None
                      ):
  if context:
    calendar_name = f'context-calendar-{user_id}.ics'
  else:
    calendar_name = f'tasks-calendar-{user_id}.ics'
  calendar_path = os.path.join('db', 'data', user_id, calendar_name)
  timezone = users[user_id]['timezone']
  if ical_obj:
    cal = ical_obj
  else:
    if os.path.isfile(calendar_path):
      log.debug(f'Reading from {calendar_path}')
      cal = icalendar.Calendar.from_ical(open(calendar_path, 'rb').read())
    else:
      log.debug(f'Making new calendar')
      if context:
        cal = constants.get_new_calendar('Time-Tracker: Context', timezone)
      else:
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
  event.add('UID', event_id)
  event.add('summary', summary)
  event.add('description', task_description)
  event.add('tzoffset', tzoffset_hours)
  event.add('dtstart', dtstart)
  event.add('dtend', dtend)
  cal.add_component(event)
  log.debug(f'Added event {event_id} to calendar')
  if ical_obj:
    return cal
  else:
    with open(calendar_path, 'wb') as f:
      log.debug(f'Writing to {calendar_path}')
      f.write(cal.to_ical())
    return

def update_task_totals(users, user_id, task_id, tz_start_time, tz_end_time, totals_obj=None):
  start_date = datetime.datetime.utcfromtimestamp(tz_start_time)
  if totals_obj:
    totals = totals_obj
  else:
    filename = f'task-totals-{user_id}'
    totals_path = os.path.join('data', user_id, filename)
    totals = db.read(totals_path)
  tz_time_total = tz_end_time - tz_start_time
  if not totals:
    totals = {'total_time':{}}
  year_number = str(start_date.year)
  month_number = str(start_date.month)
  day_number = str(start_date.day)
  if year_number not in totals.keys():
    totals[year_number] = {'total_time':{}}
  if month_number not in totals[year_number].keys():
    totals[year_number][month_number] = {'total_time':{}}
  if day_number not in totals[year_number][month_number].keys():
    totals[year_number][month_number][day_number] = {'total_time':{}}

  # All time
  try:
    totals['total_time'][task_id] += tz_time_total
  except KeyError:
    totals['total_time'][task_id] = tz_time_total
  # Year
  try:
    totals[year_number]['total_time'][task_id] += tz_time_total
  except KeyError:
    totals[year_number]['total_time'][task_id] = tz_time_total
  # Month
  try:
    totals[year_number][month_number]['total_time'][task_id] += tz_time_total
  except KeyError:
    totals[year_number][month_number]['total_time'][task_id] = tz_time_total
  # Day
  try:
    totals[year_number][month_number][day_number]['total_time'][task_id] += tz_time_total
  except KeyError:
    totals[year_number][month_number][day_number]['total_time'][task_id] = tz_time_total

  if totals_obj:
    return totals
  else:
    db.write(totals_path, totals)
    return

def add_place(users, user_id, place_name, enabled=True):
  if place_name in get_all_names(users, user_id, 'place'):
    place_id = get_id(users, user_id, 'place', place_name)
    if users[user_id]['places'][place_id]['enabled']:
      return None
    else:
      users[user_id]['places'][place_id]['enabled'] = True
      db.write('users', users)
      return f'Enabled place "{place_name}"'
  else: # adding place to db
    new_place_id = str(uuid.uuid4())
    users[user_id]['places'].update(
        {new_place_id:constants.get_default_place(place_name)}
        )
    users[user_id]['places'][new_place_id]['enabled'] = enabled
    db.write('users', users)
    return f'Added place "{place_name}"'

def stop_place(users, user_id, place_id, stop_time):
  place_name = get_name(users, user_id, 'place', place_id)
  place_start_time = users[user_id]['active_place']['start_time']
  place_end_time = stop_time
  if place_end_time <= place_start_time:
    users[user_id]['active_task'] = None
    db.write('users',users)
    return None
  timezone = users[user_id]['timezone']
  write_place_to_diary(users, user_id, place_id, place_start_time, place_end_time, timezone)
  # Writing place total time to users.json
  users[user_id]['last_place_end_time'] = place_end_time + 2
  place_duration_sec = place_end_time - place_start_time
  place_duration = datetime.timedelta(seconds=place_duration_sec)
  users[user_id]['active_place'] = None
  users[user_id]['places'][place_id]['last_active'] = place_end_time
  users[user_id]['places'][place_id]['time_total'] += place_duration_sec
  db.write('users',users)
  return place_duration

def write_place_to_diary(users, user_id, place_id, start_time, end_time, timezone, totals_obj=None):
  if not totals_obj:
    event_id = str(uuid.uuid4())
    write_to_place_list(user_id, event_id, place_id, timezone, start_time, end_time)
    write_to_place_ical(users, user_id, event_id, place_id, start_time, end_time)
  tzoffset = datetime.timezone(datetime.timedelta(hours=timezone))
  tz_start_time = timezoned(users, user_id, start_time)
  tz_end_time = timezoned(users, user_id, end_time)
  start_date = datetime.datetime.utcfromtimestamp(tz_start_time)
  end_date = datetime.datetime.utcfromtimestamp(tz_end_time)
  one_second = datetime.timedelta(seconds=1)
  while True:
    if start_date.date() == end_date.date():
      update_place_totals(users, user_id, place_id, start_date.timestamp(), end_date.timestamp(), totals_obj)
      break
    temp_end_date = start_date.replace(hour=23, minute=59, second=59)
    update_place_totals(users, user_id, place_id, start_date.timestamp(), temp_end_date.timestamp(), totals_obj)
    start_date = temp_end_date + one_second

def write_to_place_list(user_id, event_id, place_id, timezone, start_time, end_time):
  place_list_filename = f'places-{user_id}'
  place_list_path = os.path.join('data', user_id, place_list_filename)
  place_list = db.read(place_list_path)
  if not place_list: place_list = {}
  place_list[event_id] = constants.get_default_place_task(place_id, timezone, start_time, end_time)
  db.write(place_list_path, place_list)

def write_to_place_ical(users, user_id, event_id, place_id, start_time, end_time, ical_obj=None):
  calendar_name = f'places-calendar-{user_id}.ics'
  calendar_path = os.path.join('db', 'data', user_id, calendar_name)
  timezone = users[user_id]['timezone']
  if ical_obj:
    cal = ical_obj
  else:
    if os.path.isfile(calendar_path):
      log.debug(f'Reading from {calendar_path}')
      cal = icalendar.Calendar.from_ical(open(calendar_path, 'rb').read())
    else:
      log.debug(f'Making new calendar')
      cal = constants.get_new_calendar('Time-Tracker: Places', timezone)
  place_duration = end_time - start_time
  if place_duration < 60 * 60:
    place_duration /= 60
    place_duration = f' {int(place_duration)}m'
  else:
    place_duration /= 60 * 60
    place_duration = f' {place_duration:.1f}h'
  summary = users[user_id]['places'][place_id]['name'] + place_duration
  tzoffset_hours = timezone
  tzoffset_sec = tzoffset_hours * 60 * 60
  dtstart = datetime.datetime.utcfromtimestamp(start_time + tzoffset_sec)
  dtend = datetime.datetime.utcfromtimestamp(end_time + tzoffset_sec)
  event = icalendar.Event()
  event.add('UID', event_id)
  event.add('summary', summary)
  event.add('tzoffset', tzoffset_hours)
  event.add('dtstart', dtstart)
  event.add('dtend', dtend)
  cal.add_component(event)
  log.debug(f'Added event {event_id} to calendar')
  if ical_obj:
    return cal
  else:
    with open(calendar_path, 'wb') as f:
      log.debug(f'Writing to {calendar_path}')
      f.write(cal.to_ical())
    return

def update_place_totals(users, user_id, place_id, tz_start_time, tz_end_time, totals_obj=None):
  start_date = datetime.datetime.utcfromtimestamp(tz_start_time)
  if totals_obj:
    totals = totals_obj
  else:
    filename = f'place-totals-{user_id}'
    totals_path = os.path.join('data', user_id, filename)
    totals = db.read(totals_path)
  tz_time_total = tz_end_time - tz_start_time
  if not totals:
    totals = {'total_time':{}}
  year_number = str(start_date.year)
  month_number = str(start_date.month)
  day_number = str(start_date.day)
  if year_number not in totals.keys():
    totals[year_number] = {'total_time':{}}
  if month_number not in totals[year_number].keys():
    totals[year_number][month_number] = {'total_time':{}}
  if day_number not in totals[year_number][month_number].keys():
    totals[year_number][month_number][day_number] = {'total_time':{}}

  # All time
  try:
    totals['total_time'][place_id] += tz_time_total
  except KeyError:
    totals['total_time'][place_id] = tz_time_total
  # Year
  try:
    totals[year_number]['total_time'][place_id] += tz_time_total
  except KeyError:
    totals[year_number]['total_time'][place_id] = tz_time_total
  # Month
  try:
    totals[year_number][month_number]['total_time'][place_id] += tz_time_total
  except KeyError:
    totals[year_number][month_number]['total_time'][place_id] = tz_time_total
  # Day
  try:
    totals[year_number][month_number][day_number]['total_time'][place_id] += tz_time_total
  except KeyError:
    totals[year_number][month_number][day_number]['total_time'][place_id] = tz_time_total

  if totals_obj:
    return totals
  else:
    db.write(totals_path, totals)
    return

def add_tag(users, user_id, tag_name, enabled=True):
  if tag_name in get_all_tags_names(users, user_id):
    tag_id = get_tag_id(users, user_id, tag_name)
    if users[user_id]['tags'][tag_id]['enabled']:
      return None
    else:
      users[user_id]['tags'][tag_id]['enabled'] = True
      db.write('users', users)
      return f'Enabled tag "{tag_name}"'
  else: # adding tag to db
    new_tag_id = str(uuid.uuid4())
    users[user_id]['tags'].update(
        {new_tag_id:constants.get_default_tag(tag_name)}
        )
    users[user_id]['tags'][new_tag_id]['enabled'] = enabled
    db.write('users', users)
    return f'Added tag "{tag_name}"'

def get_entry_info(users, user_id, entry_id):
    if entry_id in users[user_id]['tasks'].keys():
      entry_info = users[user_id]['tasks'][entry_id]
    elif entry_id in users[user_id]['places'].keys():
      entry_info = users[user_id]['places'][entry_id]
    else:
      return None
    tags = get_entry_tags_names(users, user_id, entry_id)
    entry_tags = ''
    if tags:
      for tag in tags:
        entry_tags += f'{tag}, '
    else:
      entry_tags = 'No tags'
    date_added = timezoned(users, user_id, entry_info['date_added'])
    date_added = datetime.datetime.utcfromtimestamp(date_added)
    time_total = datetime.timedelta(seconds=entry_info['time_total'])
    time_total_hours = entry_info['time_total'] / 60 / 60
    entry_status = ''
    active_task_id = None
    active_context_id = None
    active_place_id = None
    if users[user_id]['active_task']:
      active_task_id = users[user_id]['active_task']['id']
    if users[user_id]['active_context']:
      active_context_id = users[user_id]['active_context']['id']
    if users[user_id]['active_place']:
      active_place_id = users[user_id]['active_place']['id']
    if active_task_id == entry_id or active_context_id == entry_id or active_place_id == entry_id:
      last_active = 'now'
      last_active_ago = '0m'
    else:
      if entry_info['last_active']:
        last_active = timezoned(users, user_id, entry_info['last_active'])
        last_active = datetime.datetime.utcfromtimestamp(last_active)
        last_active_ago = int(time.time()) - int(entry_info['last_active'])
        if last_active_ago > 60*60*24:
          last_active_ago = datetime.timedelta(seconds= int(time.time()) - entry_info['last_active']).days
          last_active_ago = f'{last_active_ago} days'
        else:
          last_active_ago = datetime.timedelta(seconds= int(time.time()) - entry_info['last_active'])
      else:
        last_active = 'never'
        last_active_ago = 'never'
    if not entry_info['enabled']: entry_status = ' (disabled)'
    report = f'''{get_name(users, user_id, "all", entry_id)}{entry_status}
    Tags: {entry_tags}
    Creation date: {date_added}
    Last active: {last_active} ~ {last_active_ago} ago
    Total time: {time_total} ~ {time_total_hours:.1f} hours'''
    return report

def handle_info_query(users, user_id, query='0|tasks|no-entry'):
  page_entries = 6
  columns = 2
  page, info_type, chosen_entry_id = query.split('|')
  page = int(page)
  if page < 0: page = 0
  # Last row start
  last_row = InlineKeyboardButton('<', callback_data=f'info:{page-1}|{info_type}|{chosen_entry_id}'),
  if info_type == 'tasks':
    report = 'Task: '
    last_row += InlineKeyboardButton('Show places', callback_data=f'info:{page}|places|{chosen_entry_id}'),
  elif info_type == 'places':
    report = 'Place: '
    last_row += InlineKeyboardButton('Show tasks', callback_data=f'info:{page}|tasks|{chosen_entry_id}'),
  last_row += InlineKeyboardButton('>', callback_data=f'info:{page+1}|{info_type}|{chosen_entry_id}'),
  # Last row end
  entry_id_list = list(get_all(users, user_id, info_type))
  entry_name = get_name(users, user_id, 'all', chosen_entry_id)
  if entry_name:
    report += get_entry_info(users, user_id, chosen_entry_id)
  # Keyboard generation
  options_dict = {}
  entry_slice_start = page * page_entries
  entry_slice_end = entry_slice_start + page_entries
  entry_page = list(users[user_id][info_type].keys())[entry_slice_start:entry_slice_end]
  for entry_id in entry_page:
    entry_name = users[user_id][info_type][entry_id]['name']
    options_dict.update({entry_name:f'info:{page}|{info_type}|{entry_id}'})
  keyboard = get_inline_options_keyboard(options_dict, columns)
  keyboard.append(last_row)
  reply_markup = InlineKeyboardMarkup(keyboard)
  report += f'\np. {page+1}'
  return report, reply_markup

def stats_alltime_entry(users, user_id, entry_id, entry_info):
  time_total = datetime.timedelta(seconds=entry_info['time_total'])
  time_total_hours = entry_info['time_total'] / 60 / 60
  report = f'{get_name(users, user_id, "all", entry_id)}: {time_total} ~ {time_total_hours:.1f} hours'
  return report

def stats_period_entry(users, user_id, entry_id, entry_time):
  time_total = datetime.timedelta(seconds=entry_time)
  time_total_hours = entry_time / 60 / 60
  report = f'{get_name(users, user_id, "all", entry_id)}: {time_total} ~ {time_total_hours:.1f} hours'
  return report

def handle_stats_query(users, user_id, option=None):
  stats_delta = temp_vars[user_id]['stats_delta']
  stats_info = temp_vars[user_id]['stats_info']
  stats_type = users[user_id]['stats_type']
  stats_sort = temp_vars[user_id]['stats_sort']
  timezone = users[user_id]['timezone']
  tzdelta = datetime.timezone(datetime.timedelta(hours=timezone))
  if option == 'tasks':
    stats_info = 'tasks'
    temp_vars[user_id]['stats_info'] = stats_info
  elif option == 'places':
    stats_info = 'places'
    temp_vars[user_id]['stats_info'] = stats_info
  elif option == 'by-entry':
    stats_sort = 'by-entry'
    temp_vars[user_id]['stats_sort'] = stats_sort
  elif option == 'by-tag':
    stats_sort = 'by-tag'
    temp_vars[user_id]['stats_sort'] = stats_sort
  elif option == 'alltime':
    stats_type = 'alltime'
    users[user_id]['stats_type'] = stats_type
    db.write('users', users)
  elif option == 'detailed':
    stats_type = 'detailed'
    users[user_id]['stats_type'] = stats_type
    db.write('users', users)
  elif option == 'year':
    stats_type = 'year'
    users[user_id]['stats_type'] = stats_type
    db.write('users', users)
  elif option == 'month':
    stats_type = 'month'
    users[user_id]['stats_type'] = stats_type
    db.write('users', users)
  elif option == 'day':
    stats_type = 'day'
    users[user_id]['stats_type'] = stats_type
    db.write('users', users)
  elif option == 'left':
    if stats_type == 'day':
      stats_delta += 1
    elif stats_type == 'month':
      stats_delta += 30
    elif stats_type == 'year':
      stats_delta += 365
    temp_vars[user_id]['stats_delta'] = stats_delta
  elif option == 'right':
    if stats_type == 'day':
      stats_delta -= 1
    elif stats_type == 'month':
      stats_delta -= 30
    elif stats_type == 'year':
      stats_delta -= 365
    if stats_delta < 0:
      stats_delta = 0
    temp_vars[user_id]['stats_delta'] = stats_delta

  if stats_info == 'tasks':
    stats_info_button = InlineKeyboardButton('Place stats', callback_data='stats:places')
  elif stats_info == 'places':
    stats_info_button = InlineKeyboardButton('Task stats', callback_data='stats:tasks')
  if stats_sort == 'by-entry':
    stats_sort_button = InlineKeyboardButton('by tags', callback_data='stats:by-tag')
  elif stats_sort == 'by-tag':
    stats_sort_button = InlineKeyboardButton('by entry', callback_data='stats:by-entry')

  if stats_type == 'detailed':
    entries = get_all(users, user_id, stats_info)
    entry_list = users[user_id][stats_info]
    report = 'Detailed statistics:\n--------------------'
    for entry_id in entries:
      report += '\n' + get_entry_info(users, user_id, entry_id)
    keyboard = [
        [
        InlineKeyboardButton('Day', callback_data='stats:day'),
        InlineKeyboardButton('Month', callback_data='stats:month'),
        InlineKeyboardButton('Year', callback_data='stats:year')
        ],
        [
          InlineKeyboardButton('All time', callback_data='stats:alltime')
        ],
        [
        stats_info_button,
        stats_sort_button,
        ]
      ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return report, reply_markup

  elif stats_type == 'alltime':
    if stats_sort == 'by-entry':
      report = 'All time statistics by entry\n--------------------'
      entries = get_all(users, user_id, stats_info)
      entry_list = users[user_id][stats_info]
      for entry_id in entries:
        entry_info = entry_list[entry_id]
        report += '\n\t\t\t\t' + stats_alltime_entry(users, user_id, entry_id, entry_info)
    elif stats_sort == 'by-tag':
      tags_list = get_all_tags_by_function(users, user_id, 'tag')
      report = 'All time statistics by tag\n--------------------'
      if tags_list:
        for tag_id in tags_list:
          tag_name = get_tag_name(users, user_id, tag_id)
          entry_list_ids = get_entry_ids_with_tags(users, user_id, stats_info, [tag_name])
          if entry_list_ids:
            entry_report = ''
            tag_time_total = 0
            for entry_id in entry_list_ids:
              entry_info = users[user_id][stats_info][entry_id]
              entry_report += '\n\t\t\t\t' + stats_alltime_entry(users, user_id, entry_id, entry_info)
              tag_time_total += entry_info['time_total']
            tag_time_total_str = datetime.timedelta(seconds=tag_time_total)
            tag_time_total_hours = tag_time_total / 60 / 60
            report += f'\n\nTag: {tag_name}, {tag_time_total_str} ~ {tag_time_total_hours:.1f} hours'
            report += entry_report
      else:
        report += '\nNo reportable tags'
    keyboard = [
        [
        InlineKeyboardButton('Day', callback_data='stats:day'),
        InlineKeyboardButton('Month', callback_data='stats:month'),
        InlineKeyboardButton('Year', callback_data='stats:year')
        ],
        [
          InlineKeyboardButton('Detailed', callback_data='stats:detailed')
        ],
        [
        stats_info_button,
        stats_sort_button,
        ]
      ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return report, reply_markup

  elif stats_type == 'year':
    timedelta = datetime.timedelta(days=stats_delta)
    date = datetime.datetime.now(tzdelta) - timedelta
    filename = f'{stats_info[:-1]}-totals-{user_id}'
    totals = db.read(os.path.join('data', user_id, filename))
    if totals:
      try:
        year = str(date.year)
        if stats_sort == 'by-entry':
          report = f'Year statistics by entry: {date.year}\n--------------------'
          for entry_id in totals[year]['total_time']:
            entry_time = totals[year]['total_time'][entry_id]
            report += '\n\t\t\t\t' + stats_period_entry(users, user_id, entry_id, entry_time)
        elif stats_sort == 'by-tag':
          tags_list = get_all_tags_by_function(users, user_id, 'tag')
          report = f'Year statistics by tag: {date.year}\n--------------------'
          if tags_list:
            for tag_id in tags_list:
              tag_name = get_tag_name(users, user_id, tag_id)
              entry_list_ids = get_entry_ids_with_tags(users, user_id, stats_info, [tag_name])
              if entry_list_ids:
                entry_report = ''
                tag_time_total = 0
                for entry_id in entry_list_ids:
                  if entry_id in totals[year]['total_time'].keys():
                    entry_time = totals[year]['total_time'][entry_id]
                    entry_report += '\n\t\t\t\t' + stats_period_entry(users, user_id, entry_id, entry_time)
                    tag_time_total += entry_time
                if entry_report:
                  tag_time_total_str = datetime.timedelta(seconds=tag_time_total)
                  tag_time_total_hours = tag_time_total / 60 / 60
                  report += f'\n\nTag: {tag_name}, {tag_time_total_str} ~ {tag_time_total_hours:.1f} hours'
                  report += entry_report
          else:
            report += '\nNo reportable tags'
      except KeyError:
        report += f'\nNo data for {date.year}'
    else:
      report += f'\nNo data for {date.year}'
    keyboard = [
        [
          InlineKeyboardButton('Day', callback_data='stats:day'),
          InlineKeyboardButton('Month', callback_data='stats:month')
        ],
        [
          InlineKeyboardButton('All time', callback_data='stats:alltime'),
          InlineKeyboardButton('Detailed', callback_data='stats:detailed')
        ],
        [
          InlineKeyboardButton('<', callback_data='stats:left'),
          InlineKeyboardButton('>', callback_data='stats:right'),
        ],
        [
        stats_info_button,
        stats_sort_button,
        ]
      ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return report, reply_markup

  elif stats_type == 'month':
    timedelta = datetime.timedelta(days=stats_delta)
    date = datetime.datetime.now(tzdelta) - timedelta
    filename = f'{stats_info[:-1]}-totals-{user_id}'
    totals = db.read(os.path.join('data', user_id, filename))
    if totals:
      try:
        year = str(date.year)
        month = str(date.month)
        if stats_sort == 'by-entry':
          report = f'Month statistics by entry: {year}-{month}\n--------------------'
          for entry_id in totals[year][month]['total_time']:
            entry_time = totals[year][month]['total_time'][entry_id]
            report += '\n\t\t\t\t' + stats_period_entry(users, user_id, entry_id, entry_time)
        elif stats_sort == 'by-tag':
          tags_list = get_all_tags_by_function(users, user_id, 'tag')
          report = f'Month statistics by tag: {year}-{month}\n--------------------'
          if tags_list:
            for tag_id in tags_list:
              tag_name = get_tag_name(users, user_id, tag_id)
              entry_list_ids = get_entry_ids_with_tags(users, user_id, stats_info, [tag_name])
              if entry_list_ids:
                entry_report = ''
                tag_time_total = 0
                for entry_id in entry_list_ids:
                  if entry_id in totals[year][month]['total_time'].keys():
                    entry_time = totals[year][month]['total_time'][entry_id]
                    entry_report += '\n\t\t\t\t' + stats_period_entry(users, user_id, entry_id, entry_time)
                    tag_time_total += entry_time
                if entry_report:
                  tag_time_total_str = datetime.timedelta(seconds=tag_time_total)
                  tag_time_total_hours = tag_time_total / 60 / 60
                  report += f'\n\nTag: {tag_name}, {tag_time_total_str} ~ {tag_time_total_hours:.1f} hours'
                  report += entry_report
          else:
            report += '\nNo reportable tags'
      except KeyError:
        report += f'\nNo data for {date.year}-{date.month}'
    else:
      report += f'\nNo data for {date.year}-{date.month}'
    keyboard = [
        [
          InlineKeyboardButton('Day', callback_data='stats:day'),
          InlineKeyboardButton('Year', callback_data='stats:year')
        ],
        [
          InlineKeyboardButton('All time', callback_data='stats:alltime'),
          InlineKeyboardButton('Detailed', callback_data='stats:detailed')
        ],
        [
          InlineKeyboardButton('<', callback_data='stats:left'),
          InlineKeyboardButton('>', callback_data='stats:right'),
        ],
        [
        stats_info_button,
        stats_sort_button,
        ]
      ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return report, reply_markup

  elif stats_type == 'day':
    timedelta = datetime.timedelta(days=stats_delta)
    date = datetime.datetime.now(tzdelta) - timedelta
    filename = f'{stats_info[:-1]}-totals-{user_id}'
    totals = db.read(os.path.join('data', user_id, filename))
    if totals:
      try:
        year = str(date.year)
        month = str(date.month)
        day = str(date.day)
        if stats_sort == 'by-entry':
          report = f'Day statistics by entry: {year}-{month}-{day}\n--------------------'
          for entry_id in totals[year][month][day]['total_time']:
            entry_time = totals[year][month][day]['total_time'][entry_id]
            report += '\n\t\t\t\t' + stats_period_entry(users, user_id, entry_id, entry_time)
        elif stats_sort == 'by-tag':
          tags_list = get_all_tags_by_function(users, user_id, 'tag')
          report = f'Day statistics by tag: {year}-{month}-{day}\n--------------------'
          if tags_list:
            for tag_id in tags_list:
              tag_name = get_tag_name(users, user_id, tag_id)
              entry_list_ids = get_entry_ids_with_tags(users, user_id, stats_info, [tag_name])
              if entry_list_ids:
                entry_report = ''
                tag_time_total = 0
                for entry_id in entry_list_ids:
                  if entry_id in totals[year][month][day]['total_time'].keys():
                    entry_time = totals[year][month][day]['total_time'][entry_id]
                    entry_report += '\n\t\t\t\t' + stats_period_entry(users, user_id, entry_id, entry_time)
                    tag_time_total += entry_time
                if entry_report:
                  tag_time_total_str = datetime.timedelta(seconds=tag_time_total)
                  tag_time_total_hours = tag_time_total / 60 / 60
                  report += f'\n\nTag: {tag_name}, {tag_time_total_str} ~ {tag_time_total_hours:.1f} hours'
                  report += entry_report
          else:
            report += '\nNo reportable tags'
      except KeyError:
        report += f'\nNo data for {date.year}-{date.month}-{date.day}'
    else:
      report += f'\nNo data for {date.year}-{date.month}-{date.day}'
    keyboard = [
        [
          InlineKeyboardButton('Month', callback_data='stats:month'),
          InlineKeyboardButton('Year', callback_data='stats:year')
        ],
        [
          InlineKeyboardButton('All time', callback_data='stats:alltime'),
          InlineKeyboardButton('Detailed', callback_data='stats:detailed')
        ],
        [
          InlineKeyboardButton('<', callback_data='stats:left'),
          InlineKeyboardButton('>', callback_data='stats:right'),
        ],
        [
        stats_info_button,
        stats_sort_button,
        ]
      ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return report, reply_markup
  else:
    return 'Wrong query data', None


def get_description_id(users, user_id, task_id, name):
  descriptions = users[user_id]['tasks'][task_id]['descriptions']
  for description_id in descriptions:
    if name == descriptions[description_id]['name']:
      return description_id
  return None

def get_description_names_sorted(users, user_id, task_id):
  descriptions = users[user_id]['tasks'][task_id]['descriptions']
  description_names = []
  for description_id in descriptions:
    description_names.append(descriptions[description_id]['name'])
  def description_sort(name):
    return descriptions[get_description_id(users, user_id, task_id, name)]['last_active']
  print(description_names)
  if description_names:
    description_names.sort(key=description_sort, reverse=True)
    print(description_names)
    return description_names
  else:
    return []

def get_descriptions_reply_markup(users, user_id, task_id):
  keyboard = []
  max_inline_descriptions = 2
  for description_name in get_description_names_sorted(users, user_id, task_id)[:max_inline_descriptions]:
    description_id = get_description_id(users, user_id, task_id, description_name)
    keyboard += [InlineKeyboardButton(description_name, callback_data = f'description:{description_id}')],
  keyboard += [InlineKeyboardButton('New description', callback_data = 'description:new')],
  reply_markup = InlineKeyboardMarkup(keyboard)
  return reply_markup

def handle_description_query(users, user_id, query):
  if users[user_id]['active_task']:
    try:
      description_id = query
      task_id = users[user_id]['active_task']['id']
      description_name = users[user_id]['tasks'][task_id]['descriptions'][description_id]['name']
      users[user_id]['active_task']['description'] = description_name
      db.write('users', users)
      temp_vars[user_id]['task_description'] = description_name
      return f'Description: {description_name}', None
    except KeyError:
      if query == 'new':
        tgbot.send_message(user_id, 'Type new description\n/cancel', keyboard=[])
        change_state(users, user_id, 'new_task_description')
      return 'New description', None
  else:
    return 'No active task', None

def new_description(users, user_id, description_name, entry_type):
  if entry_type == 'task':
    users[user_id]['active_task']['description'] = description_name
    temp_vars[user_id]['task_description'] = description_name
  elif entry_type == 'context':
    users[user_id]['active_context']['description'] = description_name
    temp_vars[user_id]['context_description'] = description_name
  db.write('users', users)
  return f'New description: {description_name}'

def get_tags_reply_markup(users, user_id, entry_id):
  entry_name = get_name(users, user_id, 'all', entry_id)
  reply_text = f'Tag editor: {entry_name}\n-----------------------------'
  added_tags_names = temp_vars[user_id]['tag_editor_active_tags']
  for tag_name in added_tags_names:
    reply_text += f'\n{tag_name}'
  all_tags_names = get_all_tags_names(users, user_id, enabled_only=True)
  keyboard = []
  for tag_name in all_tags_names:
    if tag_name in added_tags_names:
      tag_text = f'[{tag_name}]'
    else:
      tag_text = f'{tag_name}'
    keyboard += [InlineKeyboardButton(tag_text, callback_data = f'tag:{tag_name}')],
  keyboard += [InlineKeyboardButton('Save changes', callback_data = 'tag:save-changes')],
  reply_markup = InlineKeyboardMarkup(keyboard)
  return reply_text, reply_markup

def handle_tags_query(users, user_id, query):
  tag_editor_entry_id = temp_vars[user_id]['tag_editor_entry_id']
  tag_editor_active_tags = temp_vars[user_id]['tag_editor_active_tags']
  if tag_editor_entry_id:
    entry_name = get_name(users, user_id, 'all', tag_editor_entry_id)
    if query == 'save-changes':
      tag_ids_list = []
      for tag_name in tag_editor_active_tags: # Building list of tag ids
        tag_ids_list.append(get_tag_id(users, user_id, tag_name))
      if tag_editor_entry_id in users[user_id]['tasks'].keys(): # If entry is a task
        users[user_id]['tasks'][tag_editor_entry_id]['tags'] = tag_ids_list
        db.write('users', users)
        reply_text = f'Tag editor: {entry_name}\n-----------------------------'
        for tag_name in tag_editor_active_tags:
          reply_text += f'\n{tag_name}'
        enable_menu(users, user_id)
        return reply_text, None
      elif tag_editor_entry_id in users[user_id]['places'].keys(): # If entry is a place
        users[user_id]['places'][tag_editor_entry_id]['tags'] = tag_ids_list
        db.write('users', users)
        reply_text = f'Tag editor: {entry_name}\n-----------------------------'
        for tag_name in tag_editor_active_tags:
          reply_text += f'\n{tag_name}'
        enable_menu(users, user_id)
        return reply_text, None
    else:
      tag_name = query
      if tag_name in get_all_tags_names(users, user_id):
        if tag_name in tag_editor_active_tags:
          tag_editor_active_tags.remove(tag_name)
          temp_vars[user_id]['tag_editor_active_tags'] = tag_editor_active_tags
        else:
          tag_editor_active_tags.append(tag_name)
          temp_vars[user_id]['tag_editor_active_tags'] = tag_editor_active_tags
        return get_tags_reply_markup(users, user_id, tag_editor_entry_id)
  enable_menu(users, user_id)
  return 'Error, restart tag editor', None

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

  # STATE - new_task_description
  if state == 'new_task_description':
    reply = new_description(users, user_id, text, 'task')
    tgbot.send_message(user_id, reply, keyboard=get_main_menu(users, user_id))
    change_state(users, user_id, 'main_menu')
    get_new_timer(user_id)

  # STATE - new_context_description
  elif state == 'new_context_description':
    reply = new_description(users, user_id, text, 'context')
    tgbot.send_message(user_id, reply, keyboard=get_main_menu(users, user_id))
    change_state(users, user_id, 'main_menu')
    get_new_timer(user_id)

  # STATE - start_task
  elif state == 'start_task':
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
    task_id = get_id(users, user_id, 'task', task_name)
    if not task_id:
      add_task(users, user_id, task_name, enabled=False)
      task_id = get_id(users, user_id, 'task', task_name)
      tgbot.send_message(user_id, f'Added custom task {task_name}')
    users[user_id]['active_task'] = {
        'id': task_id,
        'start_time':start_time,
        'description':''
        }
    db.write('users',users)
    reply_markup = get_descriptions_reply_markup(users, user_id, task_id)
    tgbot.send_message(user_id,
        f'Started {task_name}', 
        keyboard=get_main_menu(users, user_id),
        )
    tgbot.send_message(user_id,
        f'No description', 
        reply_markup=reply_markup
        )
    change_state(users, user_id, 'main_menu')
    get_new_timer(user_id)

  # STATE - start_task_time
  if state == 'start_task_time':
    if text == constants.get_name('show_disabled'):
      tasks = get_disabled_names(users, user_id, 'task')
      if tasks:
        keyboard = get_options_keyboard(tasks, columns=3)
        keyboard += [constants.get_name('show_enabled')],
        tgbot.send_message(user_id, 'Choose a task to start\n/cancel', keyboard=keyboard)
      else:
        tgbot.send_message(user_id, 'No disabled tasks\n/cancel')
    elif text == constants.get_name('show_enabled'):
      tasks = get_enabled_names(users, user_id, 'task')
      keyboard = get_options_keyboard(tasks, columns=3)
      keyboard += [constants.get_name('show_disabled')],
      tgbot.send_message(user_id, 'Choose a task to start\n/cancel', keyboard=keyboard)
    else:
      task_name = text
      temp_vars[user_id].update({'task_name':task_name})
      keyboard = [[constants.get_name('now')]] + get_options_keyboard(constants.get_time_presets(), columns=4)
      tgbot.send_message(user_id, f'When to start {task_name}?\n/cancel', keyboard=keyboard)
      change_state(users, user_id, 'start_task')

  # STATE - stop_task
  elif state == 'stop_task':
    time_interval = text
    if users[user_id]['active_task']:
      task_id = users[user_id]['active_task']['id']
      task_name = get_name(users, user_id, 'task', task_id)
      task_duration = stop_task(users, user_id, task_id, time_interval)
      if task_duration != None:
        tgbot.send_message(user_id, f'Stopped {task_name}\nTime taken: {task_duration}', keyboard=get_main_menu(users, user_id))
        if users[user_id]['active_context']:
          get_new_timer(user_id, notify=False)
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
    task_id = get_id(users, user_id, 'task', task_name)
    if task_id != None:
      users[user_id]['tasks'][task_id]['enabled'] = False
      db.write('users',users)
      tgbot.send_message(user_id, f'Disabled task "{task_name}"', keyboard=get_main_menu(users, user_id))
    else:
      tgbot.send_message(user_id, f'Task "{task_name}" does not exist', keyboard=get_main_menu(users, user_id))
    change_state(users, user_id, 'main_menu')

  # STATE - start_context
  elif state == 'start_context':
    # Retroactive context starting
    if text == constants.get_name('now'):
      start_time = int(time.time())
    else:
      time_interval = convert_interval_to_seconds(text)
      if time_interval:
        start_time = max(int(time.time()) - time_interval, users[user_id]['last_context_end_time'])
      else:
        tgbot.send_message(user_id, f'Incorrect time "{text}"', keyboard=get_main_menu(users, user_id))
        change_state(users, user_id, 'main_menu')
        return

    context_name = temp_vars[user_id]['context_name']
    context_id = get_id(users, user_id, 'tasks', context_name)
    if not context_id:
      tgbot.send_message(user_id, f'Incorrect context name', keyboard=get_main_menu(users, user_id))
      change_state(users, user_id, 'main_menu')
    users[user_id]['active_context'] = {
        'id': context_id,
        'start_time':start_time,
        'description':''
        }
    db.write('users',users)
    # reply_markup = get_descriptions_reply_markup(users, user_id, task_id) ### Context description
    tgbot.send_message(user_id,
        f'Context: {context_name}', 
        keyboard=get_main_menu(users, user_id),
        )
    # tgbot.send_message(user_id, ### Context description
    #     f'No description', 
    #     reply_markup=reply_markup
    #     )
    change_state(users, user_id, 'main_menu')
    get_new_timer(user_id)

  # STATE - start_context_time
  if state == 'start_context_time':
    context_name = text
    temp_vars[user_id].update({'context_name':context_name})
    keyboard = [[constants.get_name('now')]] + get_options_keyboard(constants.get_time_presets(), columns=4)
    tgbot.send_message(user_id, f'When to start {context_name}?\n/cancel', keyboard=keyboard)
    change_state(users, user_id, 'start_context')

  # STATE - stop_context
  elif state == 'stop_context':
    time_interval = text
    if users[user_id]['active_context']:
      context_id = users[user_id]['active_context']['id']
      context_name = get_name(users, user_id, 'tasks', context_id)
      context_duration = stop_task(users, user_id, context_id, time_interval, context=True)
      if context_duration != None:
        tgbot.send_message(
            user_id,
            f'Stopped {context_name}\nTime taken: {context_duration}',
            keyboard=get_main_menu(users, user_id)
            )
        if users[user_id]['active_task']:
          get_new_timer(user_id, notify=False)
        change_state(users, user_id, 'main_menu')
      else:
        tgbot.send_message(user_id, f'Incorrect time "{text}"', keyboard=get_main_menu(users, user_id))
        change_state(users, user_id, 'main_menu')
    else:
      tgbot.send_message(user_id, f'No context is active', keyboard=get_main_menu(users, user_id))

  # STATE - change_place
  elif state == 'change_place':
    # Retroactive place changing
    if text == constants.get_name('now'):
      start_time = int(time.time())
    else:
      time_interval = convert_interval_to_seconds(text)
      if time_interval:
        start_time = max(int(time.time()) - time_interval, users[user_id]['last_place_end_time'])
      else:
        tgbot.send_message(user_id, f'Incorrect time "{text}"', keyboard=get_main_menu(users, user_id))
        change_state(users, user_id, 'main_menu')
        return

    last_place_id = None
    last_place_name = None
    last_place_duration = None
    if users[user_id]['active_place']:
      last_place_id = users[user_id]['active_place']['id']
      last_place_name = get_name(users, user_id, 'place', last_place_id)
      last_place_duration = stop_place(users, user_id, last_place_id, start_time-1)
    place_name = temp_vars[user_id]['place_name']
    place_id = get_id(users, user_id, 'place', place_name)
    if not place_id:
      add_place(users, user_id, place_name, enabled=False)
      place_id = get_id(users, user_id, 'place', place_name)
      tgbot.send_message(user_id, f'Added place {place_name}')
    users[user_id]['active_place'] = {
        'id': place_id,
        'start_time':start_time,
        }
    db.write('users',users)
    tgbot.send_message(user_id,
        f'Place changed to {place_name}\nTime taken at place "{last_place_name}": {last_place_duration}', 
        keyboard=get_main_menu(users, user_id),
        )
    change_state(users, user_id, 'main_menu')

  # STATE - change_place_time
  if state == 'change_place_time':
    if text == constants.get_name('show_disabled'):
      places = get_disabled_names(users, user_id, 'place')
      if places:
        keyboard = get_options_keyboard(places, columns=3)
        keyboard += [constants.get_name('show_enabled')],
        tgbot.send_message(user_id, 'Choose a new place\n/cancel', keyboard=keyboard)
      else:
        tgbot.send_message(user_id, 'No disabled places\n/cancel')
    elif text == constants.get_name('show_enabled'):
      places = get_enabled_names(users, user_id, 'place')
      keyboard = get_options_keyboard(places, columns=3)
      keyboard += [constants.get_name('show_disabled')],
      tgbot.send_message(user_id, 'Choose a new place\n/cancel', keyboard=keyboard)
    else:
      place_name = text
      if users[user_id]['active_place']:
        if place_name == get_name(users, user_id, 'place', users[user_id]['active_place']['id']):
          tgbot.send_message(user_id, f'"{place_name}" is the current place', keyboard=get_main_menu(users, user_id))
          change_state(users, user_id, 'main_menu')
          return
      temp_vars[user_id].update({'place_name':place_name})
      keyboard = [[constants.get_name('now')]] + get_options_keyboard(constants.get_time_presets(), columns=4)
      tgbot.send_message(user_id, f'When to change to {place_name}?\n/cancel', keyboard=keyboard)
      change_state(users, user_id, 'change_place')

  # STATE - add_place
  elif state == 'add_place':
    place_name = text
    result = add_place(users, user_id, place_name)
    if result:
      tgbot.send_message(user_id, result, keyboard=get_main_menu(users, user_id))
      change_state(users, user_id, 'main_menu')
    else:
      tgbot.send_message(user_id, f'Place "{place_name}" already exists\nChoose another name\n/cancel')

  # STATE - disable_place
  elif state == 'disable_place':
    place_name = text
    place_id = get_id(users, user_id, 'place', place_name)
    if place_id != None:
      users[user_id]['places'][place_id]['enabled'] = False
      db.write('users',users)
      tgbot.send_message(user_id, f'Disabled place "{place_name}"', keyboard=get_main_menu(users, user_id))
    else:
      tgbot.send_message(user_id, f'Place "{place_name}" does not exist', keyboard=get_main_menu(users, user_id))
    change_state(users, user_id, 'main_menu')

  # STATE - change_tags
  elif state == 'change_tags':
    entry_name = text
    entry_id = get_id(users, user_id, 'all', entry_name)
    temp_vars[user_id]['tag_editor_entry_id'] = entry_id
    temp_vars[user_id]['tag_editor_active_tags'] = get_entry_tags_names(users, user_id, entry_id)
    disable_menu(user_id)
    reply_text, reply_markup = get_tags_reply_markup(users, user_id, entry_id)
    tgbot.send_message(user_id, reply_text, reply_markup=reply_markup)
    change_state(users, user_id, 'main_menu')

  # STATE - add_tag
  elif state == 'add_tag':
    tag_name = text
    result = add_tag(users, user_id, tag_name)
    if result:
      tgbot.send_message(user_id, result, keyboard=get_main_menu(users, user_id))
      change_state(users, user_id, 'main_menu')
    else:
      tgbot.send_message(user_id, f'Tag "{tag_name}" already exists\nChoose another name\n/cancel')

  # STATE - disable_tag
  elif state == 'disable_tag':
    tag_name = text
    tag_id = get_tag_id(users, user_id, tag_name)
    if tag_id != None:
      users[user_id]['tags'][tag_id]['enabled'] = False
      db.write('users',users)
      tgbot.send_message(user_id, f'Disabled tag "{tag_name}"', keyboard=get_main_menu(users, user_id))
    else:
      tgbot.send_message(user_id, f'Tag "{tag_name}" does not exist', keyboard=get_main_menu(users, user_id))
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

    elif button_name == constants.get_name('menu_main'):
      change_menu_state(users, user_id, 'menu_main')
      tgbot.send_message(user_id, 'Main menu', keyboard=get_main_menu(users, user_id))
      get_new_timer(user_id, notify=False)

    elif button_name == constants.get_name('menu_ext'):
      change_menu_state(users, user_id, 'menu_ext')
      tgbot.send_message(user_id, 'Extended menu', keyboard=get_main_menu(users, user_id))

    elif button_name == constants.get_name('menu_stats'):
      change_menu_state(users, user_id, 'menu_stats')
      tgbot.send_message(user_id, 'Stats menu', keyboard=get_main_menu(users, user_id))

    elif button_name == constants.get_name('menu_edit'):
      change_menu_state(users, user_id, 'menu_edit')
      tgbot.send_message(user_id, 'Editing menu', keyboard=get_main_menu(users, user_id))

    elif button_name == constants.get_name('menu_settings'):
      change_menu_state(users, user_id, 'menu_settings')
      tgbot.send_message(user_id, 'Settings', keyboard=get_main_menu(users, user_id))

    elif button_name == constants.get_name('menu_edit_tasks'):
      change_menu_state(users, user_id, 'menu_edit_tasks')
      tgbot.send_message(user_id, 'Editing tasks', keyboard=get_main_menu(users, user_id))

    elif button_name == constants.get_name('menu_edit_places'):
      change_menu_state(users, user_id, 'menu_edit_places')
      tgbot.send_message(user_id, 'Editing places', keyboard=get_main_menu(users, user_id))

    elif button_name == constants.get_name('menu_edit_tags'):
      change_menu_state(users, user_id, 'menu_edit_tags')
      tgbot.send_message(user_id, 'Editing tags', keyboard=get_main_menu(users, user_id))

    elif button_name == constants.get_name('set_timezone'):
      tgbot.send_message(user_id, 'Send hour offset for UTC\nValid range (-12...+14)\n/cancel', keyboard=[])
      change_state(users, user_id, 'set_timezone')

    elif button_name == constants.get_name('get_timer'):
      get_new_timer(user_id)

    elif button_name == constants.get_name('task_description'):
      if users[user_id]['active_task']:
        task_id = users[user_id]['active_task']['id']
        descriptions = get_description_names_sorted(users, user_id, task_id)
        tgbot.send_message(user_id, 'Task description\n/cancel', keyboard=get_options_keyboard(descriptions, columns=1))
        change_state(users, user_id, 'new_task_description')
      else:
        tgbot.send_message(user_id, 'No active task', keyboard=get_main_menu(users, user_id))
        change_state(users, user_id, 'main_menu')

    elif button_name == constants.get_name('context_description'):
      if users[user_id]['active_context']:
        context_id = users[user_id]['active_context']['id']
        descriptions = get_description_names_sorted(users, user_id, context_id)
        tgbot.send_message(user_id, 'Context description\n/cancel', keyboard=get_options_keyboard(descriptions, columns=1))
        change_state(users, user_id, 'new_context_description')
      else:
        tgbot.send_message(user_id, 'No active context', keyboard=get_main_menu(users, user_id))
        change_state(users, user_id, 'main_menu')

    elif button_name == constants.get_name('start_task'):
      tasks = get_enabled_names(users, user_id, 'task')
      if tasks:
        keyboard = get_options_keyboard(tasks, columns=3)
        keyboard += [constants.get_name('show_disabled')],
        tgbot.send_message(user_id, 'Choose a task to start\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'start_task_time')
      else:
        tgbot.send_message(user_id, "You don't have any tasks")

    elif button_name == constants.get_name('add_task'):
      tgbot.send_message(user_id, 'Name a task\n/cancel', keyboard = [])
      change_state(users, user_id, 'add_task')

    elif button_name == constants.get_name('remove_task'):
      tasks = get_enabled_names(users, user_id, 'task')
      if tasks:
        keyboard = get_options_keyboard(tasks, columns=3)
        tgbot.send_message(user_id, 'Choose a task to disable\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'remove_task')
      else:
        tgbot.send_message(user_id, "No enabled tasks")

    elif button_name == constants.get_name('enable_task'):
      tasks = get_disabled_names(users, user_id, 'task')
      if tasks:
        keyboard = get_options_keyboard(tasks, columns=3)
        tgbot.send_message(user_id, 'Choose a task to enable\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'add_task')
      else:
        tgbot.send_message(user_id, "No disabled tasks")

    elif button_name == constants.get_name('task_tags'):
      tasks = get_all_names(users, user_id, 'task')
      if tasks:
        keyboard = get_options_keyboard(tasks, columns=3)
        tgbot.send_message(user_id, 'Choose a task to edit\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'change_tags')
      else:
        tgbot.send_message(user_id, "You have no tasks")

    elif button_name == constants.get_name('place_tags'):
      tasks = get_all_names(users, user_id, 'place')
      if tasks:
        keyboard = get_options_keyboard(tasks, columns=3)
        tgbot.send_message(user_id, 'Choose a place to edit\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'change_tags')
      else:
        tgbot.send_message(user_id, "You have no places")

    elif button_name == constants.get_name('entry_stats'):
      temp_vars[user_id]['stats_delta'] = 0
      report, reply_markup = handle_stats_query(users, user_id, users[user_id]['stats_type'])
      tgbot.send_message(user_id, report, reply_markup=reply_markup)

    elif button_name == constants.get_name('entry_info'):
      report, reply_markup = handle_info_query(users, user_id)
      tgbot.send_message(user_id, report, reply_markup=reply_markup)

    elif button_name == constants.get_name('add_place'):
      tgbot.send_message(user_id, 'Name a place\n/cancel', keyboard = [])
      change_state(users, user_id, 'add_place')

    elif button_name == constants.get_name('disable_place'):
      places = get_enabled_names(users, user_id, 'place')
      if places:
        keyboard = get_options_keyboard(places, columns=3)
        tgbot.send_message(user_id, 'Choose a place to disable\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'disable_place')
      else:
        tgbot.send_message(user_id, "No enabled places")

    elif button_name == constants.get_name('enable_place'):
      places = get_disabled_names(users, user_id, 'place')
      if places:
        keyboard = get_options_keyboard(places, columns=3)
        tgbot.send_message(user_id, 'Choose a place to enable\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'add_place')
      else:
        tgbot.send_message(user_id, "No disabled places")

    elif button_name == constants.get_name('add_tag'):
      tgbot.send_message(user_id, 'Name a tag\n/cancel', keyboard = [])
      change_state(users, user_id, 'add_tag')

    elif button_name == constants.get_name('disable_tag'):
      tags = get_all_tags_names(users, user_id, enabled_only=True)
      if tags:
        keyboard = get_options_keyboard(tags, columns=3)
        tgbot.send_message(user_id, 'Choose a tag to disable\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'disable_tag')
      else:
        tgbot.send_message(user_id, "No enabled tags")

    elif button_name == constants.get_name('enable_tag'):
      tags = get_all_tags_names(users, user_id, disabled_only=True)
      if tags:
        keyboard = get_options_keyboard(tags, columns=3)
        tgbot.send_message(user_id, 'Choose a tag to enable\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'add_tag')
      else:
        tgbot.send_message(user_id, "No disabled tags")

    else: 
      stop_string = constants.get_name('stop')
      stop_string_len = len(stop_string)
      context_string = constants.get_name('change_context')
      context_string_len = len(context_string)
      place_string = constants.get_name('change_place')
      place_string_len = len(place_string)

      # Button change_context or no_context
      if button_name[:context_string_len] == context_string or button_name == constants.get_name('no_context'):
        contexts = get_entry_names_with_tags(users, user_id, 'tasks', ['context'])
        if contexts:
          if users[user_id]['active_context']:
            context_id = users[user_id]['active_context']['id']
            context_name = get_name(users, user_id, 'task', context_id)
            keyboard = [[constants.get_name('now')]] + get_options_keyboard(constants.get_time_presets(), columns=4)
            tgbot.send_message(user_id, f'When to stop {context_name}?\n/cancel', keyboard=keyboard)
            change_state(users, user_id, 'stop_context')
          else:
            keyboard = get_options_keyboard(contexts, columns=3)
            tgbot.send_message(user_id, 'Choose a context to activate\n/cancel', keyboard=keyboard)
            change_state(users, user_id, 'start_context_time')
        else:
          tgbot.send_message(user_id, 'You don\'t have any tasks tagged with "context"')

      # Button change_place
      elif button_name[:place_string_len] == place_string:
        places = get_enabled_names(users, user_id, 'place')
        if places:
          if users[user_id]['active_place']:
            active_place_id = users[user_id]['active_place']['id']
            active_place_name = get_name(users, user_id, 'place', active_place_id)
            with suppress(ValueError):
              places.remove(active_place_name)
          keyboard = get_options_keyboard(places, columns=3)
          keyboard += [constants.get_name('show_disabled')],
          tgbot.send_message(user_id, 'Choose a new place\n/cancel', keyboard=keyboard)
          change_state(users, user_id, 'change_place_time')
        else:
          tgbot.send_message(user_id, "You don't have any places")

      # Button stop_task
      elif button_name[:stop_string_len] == stop_string:
        task_id = users[user_id]['active_task']['id']
        task_name = get_name(users, user_id, 'task', task_id)
        keyboard = [[constants.get_name('now')]] + get_options_keyboard(constants.get_time_presets(), columns=4)
        tgbot.send_message(user_id, f'When to stop {task_name}?\n/cancel', keyboard=keyboard)
        change_state(users, user_id, 'stop_task')

      else: # No mathed button
        tgbot.send_message(user_id, 'Error, try again', keyboard=get_main_menu(users, user_id))
