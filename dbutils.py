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
import logic
import csv

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
  default_place = constants.get_default_place('::corrupted::')
  for user in users:
    default_tags = constants.get_default_user('::username::')['tags']
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
    for place in users[user]['places']:
      log.info(f'Checking place {place}')
      for key in default_place:
        if key not in users[user]['places'][place].keys():
          missing_total += 1
          value = default_place[key]
          users[user]['places'][place][key] = value
          log.info(f'Missing key "{key}", adding {key}:{value}')
    log.info(f'Checking tags')
    user_tag_names = []
    for tag_id in users[user]['tags']:
      user_tag_names.append(users[user]['tags'][tag_id]['name'])
    for tag_id in default_tags:
      tag_name = default_tags[tag_id]['name']
      if tag_name not in user_tag_names:
        users[user]['tags'][tag_id] = default_tags[tag_id]
        missing_total += 1
        log.info(f'Missing tag "{tag_name}", adding {tag_id}:{default_tags[tag_id]}')
    log.info(f'Checking options')
    for option in default_user['options']:
      if option not in users[user]['options'].keys():
        value = default_user['options'][option]
        users[user]['options'].update({option:value})
        missing_total += 1
        log.info(f'Missing option "{option}", adding {option}:{value}')
  if missing_total > 0: db.write('users', users)
  log.info(f'Checked users.json, {missing_total} missing entries created')
  return missing_total

def update_task_lists(dry_run):
  updated_total = 0
  log.info('Updating task lists...')
  users = db.read('users')
  for user_id in users:
    updated_local = 0
    filename = f'tasks-{user_id}'
    path = os.path.join('data', user_id, filename)
    log.info(f'Checking {path}')
    task_list = db.read(path)
    new_task_list = {}
    if task_list:
      for event in task_list:
        if 'description' not in event.keys():
          event['description'] = ''
        event_id = str(uuid.uuid4())
        new_task_list[event_id] = event
        log.debug(f'Created new event with id {event_id}')
        updated_total += 1
        updated_local += 1
      log.info(f'{updated_local} events created for user {user_id}')
      if dry_run:
        log.info(f'--dry-run, not writing changes to "{path}"')
      else:
        db.write(path, new_task_list)
    else:
      log.info(f'No task list found for user {user_id}, skipping')
  log.info(f'Updated task lists, {updated_total} entries created')

def is_uuid4(string):
  try:
    val = uuid.UUID(string, version=4)
    return True
  except ValueError:
    return False

def update_task_ids(force, dry_run):
  log.info('---------------------------')
  log.info('Updating task IDs...')
  updated_tasks = 0
  updated_data = 0
  users = db.read('users')
  for user_id in users:
    #Updating tasks
    log.info(f'Updating tasks for user {user_id}')
    task_id_dict = {}
    for old_task_id in users[user_id]['tasks'].copy():
      if is_uuid4(old_task_id) and not force:
        log.warning(f'Key for task {old_task_id} is a valid uuid4 and --force is not specified, aborting')
        return
      new_task_id = str(uuid.uuid4())
      users[user_id]['tasks'][new_task_id] = users[user_id]['tasks'][old_task_id]
      users[user_id]['tasks'].pop(old_task_id)
      task_id_dict[old_task_id] = new_task_id
      log.info(f'Key for task "{old_task_id}" changed to {new_task_id}')
      updated_tasks += 1
    #Writing changes to user
    if dry_run:
      log.info('--dry-run, not writing changes to "users"')
    else:
      db.write('users', users)
    #Updating data
    log.info('Updating data for user {user_id}')
    data_dir = os.path.join('db', 'data', user_id)
    for path, subdirs, files in os.walk(data_dir):
      for name in files:
        if f'tasks-{user_id}' in name:
          db_name = os.path.join(path, name)[3:-5] # remove "db/" and ".json" from name
          log.info(f'Updating task_list {db_name}')
          task_list = db.read(db_name)
          for event in task_list:
            old_task_id = event['id']
            new_task_id = task_id_dict[str(old_task_id)]
            event['id'] = new_task_id
            log.info(f'Changed "{old_task_id}" to "{new_task_id}"')
          if dry_run:
            log.info(f'--dry-run, not writing changes to "{db_name}"')
          else:
            db.write(db_name, task_list)
        elif 'calendar' in name:
          pass
        else:
          missing_local = 0
          db_name = os.path.join(path, name)[3:-5] # remove "db/" and ".json" from name
          log.info(f'Updating {db_name}')
          diary = db.read(db_name)
          log.info('Updating tasks_total')
          for old_task_id in diary['tasks_total'].copy():
            if is_uuid4(old_task_id) and not force:
              log.warning(f'Key for task {old_task_id} is a valid uuid4 and --force is not specified, aborting')
              return
            new_task_id = task_id_dict[old_task_id]
            diary['tasks_total'][new_task_id] = diary['tasks_total'][old_task_id]
            diary['tasks_total'].pop(old_task_id)
            log.info(f'Changed "{old_task_id}" to "{new_task_id}"')
            updated_data += 1
          for day in diary['days']:
            log.info(f'Updating day {day}')
            log.info(f'Updating tasks_total')
            for old_task_id in diary['days'][day]['tasks_total'].copy():
              if is_uuid4(old_task_id) and not force:
                log.warning(f'Key for task {old_task_id} is a valid uuid4 and --force is not specified, aborting')
                return
              new_task_id = task_id_dict[old_task_id]
              diary['days'][day]['tasks_total'][new_task_id] = diary['days'][day]['tasks_total'][old_task_id]
              diary['days'][day]['tasks_total'].pop(old_task_id)
              log.info(f'Changed "{old_task_id}" to "{new_task_id}"')
              updated_data += 1
          if dry_run:
            log.info(f'--dry-run, not writing changes to "{db_name}"')
          else:
            db.write(db_name, diary)
  log.info(f'Complete, {updated_tasks} tasks updated, {updated_data} entries updated')

def generate_task_lists(force, dry_run):
  log.info('---------------------------')
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
    try:
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
            tzoffset_sec = timezone * 60 * 60
            for task in diary['days'][day]['tasks']:
              task_id = task['id']
              start_time = int(task['start_time'] - tzoffset_sec)
              end_time = int(task['end_time'] - tzoffset_sec)
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
    except FileNotFoundError:
      log.warning(f'Path {folder} does not exist, skipping')
  log.info(f'{entries_total} total entries created')

def generate_calendars(force, dry_run):
  log.info('---------------------------')
  log.info('Started calendar generation')
  users = db.read('users')
  entries_total = 0
  for user_id in users:
    calendar_name = f'tasks-calendar-{user_id}.ics'
    calendar_path = os.path.join('db', 'data', user_id, calendar_name)
    if os.path.isfile(calendar_path) and not force:
      log.warning(f'{calendar_path} already exists and --force is not specified, aborting')
      return
    try:
      log.info(f'Generating {calendar_name} for user {user_id}')
      timezone = users[user_id]['timezone']
      cal = constants.get_new_calendar('Time-Tracker: Tasks', timezone)
      events_total = 0
      tasks = db.read(os.path.join('data', user_id, f'tasks-{user_id}'))
      if tasks:
        for event_id in tasks:
          task_id = str(tasks[event_id]['id'])
          description = tasks[event_id]['description']
          start_time = tasks[event_id]['start']
          end_time = tasks[event_id]['end']
          cal = logic.write_to_task_ical(users, user_id, event_id, task_id, description, start_time, end_time, ical_obj=cal)
          events_total += 1
          entries_total += 1
        log.info(f'Generated {events_total} events for {calendar_path}')
      if dry_run:
        log.info(f'--dry-run, not writing {calendar_path}')
      else:
        with open(calendar_path, 'wb') as f:
          log.debug(f'Writing to {calendar_path}')
          f.write(cal.to_ical())
    except FileNotFoundError:
      log.info(f'File not found, skipping user {user_id}')
  log.info(f'Created total of {entries_total} entries for {len(users)} calendars')

def generate_task_totals(force, dry_run):
  log.info('---------------------------')
  log.info('Started totals generation')
  total_entries = 0
  users = db.read('users')
  for user_id in users:
    try:
      task_list_path = os.path.join('data', user_id, f'tasks-{user_id}')
      tasks = db.read(task_list_path)
      if tasks:
        log.info(f'Generating totals for user {user_id}')
        user_entries = 0
        totals_path = os.path.join('data', user_id, f'task-totals-{user_id}')
        if db.read(totals_path) and not force:
          log.warning(f'{totals_path} already exists and --force is not specified, aborting')
          return
        totals = {'total_time':{}}
        for task in tasks:
          task_id = task['id']
          timezone = task['timezone']
          start_time = task['start']
          end_time = task['end']
          logic.write_task_to_diary(users, user_id, task_id, start_time, end_time, timezone, totals)
          total_entries += 1
          user_entries += 1
        log.info(f'{user_entries} generated for user {user_id}')
        if dry_run:
          log.info(f'--dry-run, not writing {totals_path}')
        else:
          db.write(totals_path, totals)
    except FileNotFoundError:
      log.info(f'File not found, skipping user {user_id}')
  log.info(f'Generated a total of {total_entries} entries for {len(users)} users')

def generate_descriptions(no_dry_run):
  log.info('---------------------------')
  log.info('Started description generation')
  total_entries = 0
  users = db.read('users')
  for user_id in users:
    if no_dry_run:
      log.info('Cleaning descriptions')
      for task_id in users[user_id]['tasks'].keys():
        users[user_id]['tasks'][task_id].update({'descriptions':{}})
      db.write('users', users)
    else:
      log.info('Dry run! NOT writing changes')
    try:
      task_list_path = os.path.join('data', user_id, f'tasks-{user_id}')
      context_list_path = os.path.join('data', user_id, f'context-{user_id}')
      files = [task_list_path, context_list_path]
      for filename in files:
        tasks = db.read(filename)
        if tasks:
          log.info(f'Generating descriptions from {filename} for user {user_id}')
          user_entries = 0
          for event_id in tasks:
            task_id = str(tasks[event_id]['id'])
            description = tasks[event_id]['description']
            start_time = tasks[event_id]['start']
            end_time = tasks[event_id]['end']
            description_name = tasks[event_id]['description']
            if no_dry_run:
              logic.write_task_description(users, user_id, task_id, description_name, start_time, end_time)
            total_entries += 1
            user_entries += 1
          log.info(f'{user_entries} scanned entries for user {user_id}')
    except FileNotFoundError:
      log.info(f'File not found, skipping user {user_id}')
  if no_dry_run:
    log.info('Changes were written!')
  else:
    log.info('Dry run! Changes were NOT written')
  log.info(f'Scanned a total of {total_entries} entries for {len(users)} users')

def export_to_csv():
  log.info('---------------------------')
  log.info('Started exporting to csv')
  users = db.read('users')
  for user_id in users:
    log.info(f'User {user_id}')
    log.info(f'Exporting tasks')
    user_tasks = users[user_id]['tasks']
    task_totals = db.read(os.path.join('data', user_id, f'task-totals-{user_id}'))
    with open(os.path.join('db', 'data', user_id, 'tasks-daily.csv'), mode='w') as f:
      fieldnames = ['date']
      for task_id in user_tasks:
        fieldnames.append(user_tasks[task_id]['name'])
      writer = csv.DictWriter(f, fieldnames=fieldnames)
      writer.writeheader()
      for year in task_totals:
        if year != 'total_time':
          for month in task_totals[year]:
            if month != 'total_time':
              for day in task_totals[year][month]:
                if day != 'total_time':
                  date = datetime.date(int(year), int(month), int(day))
                  row = {'date':date}
                  for task_id in task_totals[year][month][day]['total_time'].keys():
                    task_name = user_tasks[task_id]['name']
                    task_time = int(task_totals[year][month][day]['total_time'][task_id])
                    row[task_name] = task_time
                  writer.writerow(row)
  log.info('Finished exporting to csv')

@easyargs
class DButils(object):
  """Database utility"""

  # def update_task_lists(self, dry_run=False):
  #   '''
  #   Task list update (v0.10.0)
  #   :param dry_run: Do not write changes
  #   '''
  #   db.archive('update_task_lists')
  #   update_task_lists(dry_run)

  # def generate_task_totals(self, force=False, dry_run=False):
  #   '''
  #   Generate task totals
  #   :param force: Force generate if totals already exists
  #   :param dry_run: Do not write changes
  #   '''
  #   db.archive('generate_task_totals')
  #   generate_task_totals(force, dry_run)

  def generate_calendars(self, force=False, dry_run=False):
    '''
    Generate iCalendar files
    :param force: Force generate if calendar already exists
    :param dry_run: Do not write changes
    '''
    db.archive('generate_calendars')
    generate_calendars(force, dry_run)

  def generate_descriptions(self, no_dry_run=False):
    '''
    Generate descriptions
    :param no_dry_run: Write changes
    '''
    if no_dry_run:
      db.archive('generate_descriptions')
    generate_descriptions(no_dry_run)

  def export_to_csv(self):
    '''
    Export data to csv
    '''
    export_to_csv()

  # DATA removed in v0.9.0
  # def generate_task_lists(self, force=False, dry_run=False):
  #   '''
  #   Generate task list files
  #   :param force: Force generate if task list already exists
  #   :param dry_run: Do not write changes
  #   '''
  #   db.archive('generate_task_lists')
  #   generate_task_lists(force, dry_run)

  # DATA removed in v0.9.0
  # def task_id_update(self, force=False, dry_run=False):
  #   '''
  #   Tasks update to UUID (v0.8.0)
  #   :param force: Force update even if id is already integer
  #   :param dry_run: Do not write changes
  #   '''
  #   db.archive('task_id_update')
  #   update_task_ids(force, dry_run)

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
    log.info('---------------------------')
    log.info(f'Database check started on {date}')
    db.archive(filename='chkdb')
    missing_total += check_params()
    missing_total += check_users()
    # missing_total += check_data() # DATA removed in v0.9.0
    log.info(f'Database check complete, total of {missing_total} missing entries created')

if __name__ == '__main__':
  log.info('================================')
  log.info('DButils started')
  DButils()
