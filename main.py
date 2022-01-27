import os
import sys
import getopt
import time
import datetime
import telegram
import logging
from contextlib import suppress
import telegram.ext
from telegram.ext import CommandHandler, MessageHandler, Filters
import db
import traceback
import tgbot
import logic

VERSION = '0.6.0'
NAME = 'Time Tracker'

# Logger setup
with suppress(FileExistsError):
  os.makedirs('logs')
  print('Created logs folder')

log = logging.getLogger('main')
log.setLevel(logging.DEBUG)

filename = datetime.datetime.now().strftime('%Y-%m-%d') + '.log'
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

tg_token = None

try:
  args, values = getopt.getopt(sys.argv[1:],"h",["tg-token="])
  for arg, value in args:
    if arg in ('--tg-token'):
      tg_token = value
except getopt.GetoptError:
  print('-h, --tg-token')
  sys.exit(2)

log.info('=============================')
log.info(f'{NAME} v{VERSION} start')

try:
  if not tg_token:
    tg_token = os.environ['TG_TOKEN']

  log.info('Connecting to telegram...')
  tg = telegram.Bot(tg_token)
  tg.get_me()
  log.info('Connected to telegram')
  tgbot.tg = tg
except Exception:
  log.error(traceback.format_exc())
  sys.exit(2)

def mainloop():
  params = db.read('params')
  update_interval = params['update_interval']
  last_backup = params['last_backup']
  while True:
    # Backup check
    date = datetime.datetime.now().date()
    if str(date) != params['last_backup']:
      db.archive(filename='time-tracker', max_backups=10)
      params['last_backup'] = str(date)
      db.write('params', params)
    # Timer update
    logic.update_all_timers()
    # log.debug(f'Update complete, sleeping for {update_interval} seconds')
    time.sleep(update_interval)

if __name__ == '__main__':
  try:
    db.init('users')
    params = db.init('params')
    whitelist = db.init('whitelist')
    date = datetime.datetime.now().date()
    if str(date) != params['last_backup']:
      db.archive(filename='time-tracker', max_backups=10)
      params['last_backup'] = str(date)
      db.write('params', params)
    with suppress(FileExistsError):
      path = os.path.join('db', 'data')
      os.makedirs(path)
      log.info(f'Created {path} folder')
    admin_id = params['admin']
    if admin_id:
      msg = f'{NAME} v{VERSION}'
      msg += f'\nUpdate interval: {params["update_interval"]}'
      if params['use_whitelist']:
        msg += f'\nWhitelist enabled, users:'
        for user in whitelist:
          msg += f'\n  {user}'
      else:
        msg += f'Whitelist disabled'
      tg.send_message(chat_id=admin_id, text = msg, disable_notification=True)
    updater = tgbot.start(tg_token)
    mainloop()
  except Exception as e:
    log.warning('Stopping updater...')
    updater.stop()
    log.error((traceback.format_exc()))
    admin_id = db.read('params')['admin']
    if admin_id:
      tg.send_message(admin_id, f'Exception: {e}', disable_notification=True)
    sys.exit(2)
