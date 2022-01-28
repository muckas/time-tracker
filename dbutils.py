import logging
import os
import time
import datetime
from contextlib import suppress
import constants
import db
import easyargs
import icalendar
import uuid

# Logger setup
with suppress(FileExistsError):
  os.makedirs('logs')
  print('Created logs folder')

log = logging.getLogger('main')
log.setLevel(logging.DEBUG)

filename = 'dbutils-' + datetime.datetime.now().strftime('%Y-%m-%d') + '.log'
file = logging.FileHandler(os.path.join('logs', filename))
file.setLevel(logging.DEBUG)
fileformat = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
file.setFormatter(fileformat)
log.addHandler(file)

stream = logging.StreamHandler()
stream.setLevel(logging.DEBUG)
streamformat = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
stream.setFormatter(fileformat)
log.addHandler(stream)
# End of logger setup


def check_params():
  missing_total = 0
  log.info('Checking params.json...')
  params_default = db.read('params.defaults')
  params = db.read('params')
  for param in params_default:
    if param not in params.keys():
      missing_total += 1
      value = params_default[param]
      params[param] = value
      log.info(f'Missing key "{param}", added {param}:{value} ')
  if missing_total > 0: db.write('params', params)
  log.info(f'Checked params.json, {missing_total} missing entries created')
  return missing_total

def check_users():
  missing_total = 0
  log.info('Checking users.json...')
  users = db.read('users')
  default_user = constants.get_default_user('::corrupted::')
  default_task = constants.get_default_task('::corrupted::')
  for user in users:
    log.info(f'Checking user {user}')
    for key in default_user:
      if key not in users[user].keys():
        missing_total += 1
        value = default_user[key]
        users[user][key] = value
        log.info(f'Missing key "{key}", adding {key}:{value}')
    for task in users[user]['tasks']:
      log.info(f'Checking task {task}')
      for key in default_task:
        if key not in users[user]['tasks'][task].keys():
          missing_total += 1
          value = default_task[key]
          users[user]['tasks'][task][key] = value
          log.info(f'Missing key "{key}", adding {key}:{value}')
  if missing_total > 0: db.write('users', users)
  log.info(f'Checked users.json, {missing_total} missing entries created')
  return missing_total

def check_data():
  log.info('Checking data...')
  missing_total = 0
  default_diary = constants.get_defaul_diary()
  default_day= constants.get_default_day(0)
  data_dir = os.path.join('db', 'data')
  for path, subdirs, files in os.walk(data_dir):
    for name in files:
      missing_local = 0
      if name[:5] == 'tasks': # Skip tasks-{user_id}.json
        pass
      else:
        db_name = os.path.join(path, name)[3:-5] # remove "db/" and ".json" from name
        log.info(f'Checking {db_name}')
        diary = db.read(db_name)
        for key in default_diary:
          if key not in diary.keys():
            missing_local += 1
            value = default_diary[key]
            diary[key] = value
            log.info(f'Missing key "{key}", adding {key}:{value}')
        for day in diary['days']:
          log.info(f'Checking day {day}')
          for key in default_day:
            if key not in diary['days'][day].keys():
              missing_total += 1
              value = default_day[key]
              diary['days'][day][key] = value
              log.info(f'Missing key "{key}", adding {key}:{value}')
          #diary['days'][day]['history'] check goes here ============================
        if missing_local > 0: db.write(db_name, diary)
        missing_total += missing_local
        missing_local = 0
    log.info(f'Data check complete, {missing_total} missing entries created')
  return missing_total

def update_task_ids(force, dry_run):
  log.info('Updating task IDs...')
  updated_tasks = 0
  updated_data = 0
  users = db.read('users')
  for user_id in users:
    #Updating tasks
    log.info(f'Updating tasks for user {user_id}')
    task_id_dict = {}
    task_id = 0
    for task_name in users[user_id]['tasks'].copy():
      if task_name.isdigit() and not force:
        log.warning(f'Key for task {task_name} is an integer and --force is not specified, aborting')
        return
      users[user_id]['tasks'][task_id] = users[user_id]['tasks'][task_name]
      users[user_id]['tasks'][task_id]['name'] = task_name
      users[user_id]['tasks'].pop(task_name)
      task_id_dict[task_name] = task_id
      log.info(f'Key for task "{task_name}" changed to {task_id}')
      updated_tasks += 1
      task_id += 1
    #Updating data
    log.info('Updating data for user {user_id}')
    data_dir = os.path.join('db', 'data', user_id)
    for path, subdirs, files in os.walk(data_dir):
      for name in files:
        missing_local = 0
        db_name = os.path.join(path, name)[3:-5] # remove "db/" and ".json" from name
        log.info(f'Updating {db_name}')
        diary = db.read(db_name)
        log.info('Updating tasks_total')
        for task_name in diary['tasks_total'].copy():
          if task_name.isdigit() and not force:
            log.warning(f'Key for task {task_name} is an integer and --force is not specified, aborting')
            return
          task_id = task_id_dict[task_name]
          diary['tasks_total'][task_id] = diary['tasks_total'][task_name]
          diary['tasks_total'].pop(task_name)
          log.info(f'Changed "{task_name}" to "{task_id}"')
          updated_data += 1
        for day in diary['days']:
          log.info(f'Updating day {day}')
          log.info(f'Updating tasks_total')
          for task_name in diary['days'][day]['tasks_total'].copy():
            if task_name.isdigit() and not force:
              log.warning(f'Key for task {task_name} is an integer and --force is not specified, aborting')
              return
            task_id = task_id_dict[task_name]
            diary['days'][day]['tasks_total'][task_id] = diary['days'][day]['tasks_total'][task_name]
            diary['days'][day]['tasks_total'].pop(task_name)
            log.info(f'Changed "{task_name}" to "{task_id}"')
            updated_data += 1
          # Updating history
          log.info('Updating history')
          task_list = []
          updated_entries = 0
          for entry in diary['days'][day]['history'].copy():
            entry['id'] = task_id_dict[entry['name']]
            entry.pop('name')
            task_list.append(entry)
            updated_data += 1
            updated_entries += 1
          diary['days'][day]['tasks'] = task_list
          diary['days'][day].pop('history')
          log.info(f'{updated_entries} entries moved from "history" to "tasks"')
        if dry_run:
          log.info(f'--dry-run, not writing changes to "{db_name}"')
        else:
          db.write(db_name, diary)
  if dry_run:
    log.info('--dry-run, not writing changes to "users"')
  else:
    db.write('users', users)
  log.info(f'Complete, {updated_tasks} tasks updated, {updated_data} entries updated')

def generate_task_lists(force, dry_run):
  log.info('Started task list generaion')
  users = db.read('users')
  task_list = []
  entries_total = 0
  for user_id in users:
    task_list_path = os.path.join('data', user_id, f'tasks-{user_id}')
    if db.read(task_list_path) and not force:
      log.warning(f'{task_list_path} already exists and --force is not specified, aborting')
      return
    user_total = 0
    log.info(f'User {user_id}')
    folder = os.path.join('db', 'data', user_id)
    files = os.listdir(folder)
    files = [os.path.join(folder, f) for f in files] # add path to each file
    files.sort(key=lambda x: os.path.getmtime(x))
    for file in files:
      if 'tasks' in file:
        pass
      else:
        db_name = file[3:-5] # remove "db/" and ".json" from name
        log.info(f'Data {db_name}')
        data_total = 0
        diary = db.read(db_name)
        for day in diary['days']:
          log.info(f'Day {day}')
          timezone = int(diary['days'][day]['timezone'])
          for task in diary['days'][day]['tasks']:
            task_id = task['id']
            start_time = int(task['start_time'])
            end_time = int(task['end_time'])
            task_list.append(constants.get_default_list_task(task_id, timezone, start_time, end_time))
            data_total += 1
            user_total += 1
            entries_total += 1
        log.info(f'{data_total} entries for {db_name}')
    log.info(f'{user_total} entries for user {user_id}')
    if dry_run:
      log.info(f'--dry-run, not writing {task_list_path}')
    else:
      db.write(task_list_path, task_list)
  log.info(f'{entries_total} total entries created')

def generate_calendars(force, dry_run):
  log.info('Started calendar generation')
  users = db.read('users')
  entries_total = 0
  for user_id in users:
    calendar_name = f'tasks-calendar-{user_id}.ics'
    calendar_path = os.path.join('db', 'data', user_id, calendar_name)
    if os.path.isfile(calendar_path) and not force:
      log.warning(f'{calendar_path} already exists and --force is not specified, aborting')
      return
    log.info(f'Generating {calendar_name} for user {user_id}')
    events_total = 0
    timezone = users[user_id]['timezone']
    cal = constants.get_new_calendar('Time-Tracker-Tasks', timezone)
    task_list = db.read(os.path.join('data', user_id, f'tasks-{user_id}'))
    for task in task_list:
      task_id = str(task['id'])
      summary = users[user_id]['tasks'][task_id]['name']
      tzoffset_hours = task['timezone']
      tzoffset_sec = tzoffset_hours * 60 * 60
      dtstart = datetime.datetime.utcfromtimestamp(task['start'] + tzoffset_sec)
      dtend = datetime.datetime.utcfromtimestamp(task['end'] + tzoffset_sec)
      event = icalendar.Event()
      event.add('UID', uuid.uuid4())
      event.add('summary', summary)
      event.add('tzoffset', tzoffset_hours)
      event.add('dtstart', dtstart)
      event.add('dtend', dtend)
      cal.add_component(event)
      events_total += 1
      entries_total += 1
    log.info(f'Generated {events_total} events for {calendar_path}')
    if dry_run:
      log.info(f'--dry-run, not writing {calendar_path}')
    else:
      with open(calendar_path, 'wb') as f:
        f.write(cal.to_ical())
      log.info(f'Created {calendar_path}')
  log.info(f'Created total of {entries_total} entries for {len(users)} calendars')

@easyargs
class DButils(object):
  """Database utility"""

  def generate_calendars(self, force=False, dry_run=False):
    '''
    Generate iCalendar files
    :param force: Force generate if calendar already exists
    :param dry_run: Do not write changes
    '''
    db.archive('generate_calendars')
    generate_calendars(force, dry_run)

  def generate_task_lists(self, force=False, dry_run=False):
    '''
    Generate task list files
    :param force: Force generate if task list already exists
    :param dry_run: Do not write changes
    '''
    db.archive('generate_task_lists')
    generate_task_lists(force, dry_run)

  def task_id_update(self, force=False, dry_run=False):
    '''
    Tasks ID update (v0.7.0)
    :param force: Force update even if id is already integer
    :param dry_run: Do not write changes
    '''
    db.archive('task_id_update')
    update_task_ids(force, dry_run)

  def backup(self, name='backup', max_backups=0):
    '''
    Backup database
    :param name: Archive name
    :param max_backups: Max number of backups (if exceedes, removes oldest backups), 0 for infinite
    '''
    db.archive(filename=name, max_backups=max_backups)

  def chkdb(self, backup=True):
    """
    Check database for missing keys and add them
    :param backup: Backup database before checking
    """
    missing_total = 0
    date = datetime.datetime.now()
    log.info(f'Database check started on {date}')
    db.archive(filename='update')
    missing_total += check_params()
    missing_total += check_users()
    missing_total += check_data()
    log.info(f'Database check complete, total of {missing_total} missing entries created')

if __name__ == '__main__':
  log.info('================================')
  log.info('DButils started')
  DButils()
