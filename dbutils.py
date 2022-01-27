import logging
import os
import time
import datetime
from contextlib import suppress
import constants
import db
import easyargs

# Logger setup
with suppress(FileExistsError):
  os.makedirs('logs')
  print('Created logs folder')

log = logging.getLogger('main')
log.setLevel(logging.DEBUG)

filename = 'chkdb-' + datetime.datetime.now().strftime('%Y-%m-%d') + '.log'
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
  log.info('Checking params.json')
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
  log.info('Checking users.json')
  users = db.read('users')
  default_user = constants.get_default_user('::corrupted::')
  default_task = constants.get_default_task()
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
  log.info('Checking data')
  missing_total = 0
  default_diary = constants.get_defaul_diary()
  default_day= constants.get_default_day(0)
  data_dir = os.path.join('db/data')
  for path, subdirs, files in os.walk(data_dir):
    for name in files:
      missing_local = 0
      db_name = os.path.join(path, name)[3:-5] # remove "db/" from name
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
        #diary['days'][day]['history'] check goes here
      if missing_local > 0: db.write(db_name, diary)
      missing_total += missing_local
      missing_local = 0
  log.info(f'Data check complete, {missing_total} missing entries created')
  return missing_total

@easyargs
class DButils(object):
  """Database utility"""

  def backup(self, name='backup', max_backups=0):
    '''
    Backup database
    :param name: Archive name
    :param max_backups: Max number of backups (if exceedes, removes oldest backups) 0 for infinite
    '''
    db.archive(filename=name)

  def chkdb(self):
    """
    Check database for missing keys and add them
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
  DButils()
