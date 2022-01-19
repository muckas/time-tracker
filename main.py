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

VERSION = '0.1.0'
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
except Exception:
  log.error(traceback.format_exc())
  sys.exit(2)

help_text = '''I am sorry, but there's nothing I can help you with...'''

def tg_send_message(user_id, text, silent=False):
  users = db.read('users')
  username = users[user_id]['username']
  tg.send_message(chat_id=user_id, text=text, disable_notification=silent)
  log.info(f'Message to @{username}({user_id}):{text}')

def log_message(update):
  user_id = str(update.message.chat['id'])
  text = update.message.text
  users = db.read('users')
  username = users[user_id]['username']
  log.info(f'Message from @{username}({user_id}):{text}')

def add_user_to_db(update):
  user_id = str(update.message.chat['id'])
  log.info(f'Adding new user {user_id} to database')
  users = db.read('users')
  tg_username = str(update.message.chat['username'])
  users.update({user_id:{'username':tg_username, 'tasks':{}}})
  db.write('users', users)
  log.info(f'Added @{tg_username} to database')

def start_command(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  if validated(update):
    tg_send_message(user_id, help_text)

def validated(update, notify=False):
  user_id = str(update.message.chat['id'])
  users = db.read('users')
  if user_id not in users:
    add_user_to_db(update)
  whitelist = db.read('whitelist')
  if db.read('params')['use_whitelist']:
    if user_id in whitelist:
      log.debug(f'User {user_id} whitelisted')
      return True
    else:
      log.debug(f'User {user_id} not whitelisted')
      if notify:
        tg_send_message(user_id, f"Your id is {user_id}")
      return False
  else:
    return True

def help_command(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  if validated(update, notify=True):
    tg_send_message(user_id, help_text)

def handle_message(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  if validated(update):
    tg_send_message(user_id, update.message.text)

def mainloop():
  try:
    while True:
      pass
  except Exception as e:
    log.error(traceback.format_exc())
    admin_id = db.read('params')['admin']
    if admin_id:
      error_msg = '{NAME} stopped with an exception'
      tg.send_message(chat_id=admin_id, text = error_msg, disable_notification=True)
    return 0

if __name__ == '__main__':
  try:
    db.init('users')
    params = db.init('params')
    whitelist = db.init('whitelist')
    admin_id = params['admin']
    if admin_id:
      msg = f'{NAME} v{VERSION}\n'
      if params['use_whitelist']:
        msg += f'Whitelist enabled, users:'
        for user in whitelist:
          msg += f'\n  {user}'
      else:
        msg += f'Whitelist disabled'
      tg.send_message(chat_id=admin_id, text = msg, disable_notification=True)
    updater = telegram.ext.Updater(tg_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('start', start_command))
    updater.start_polling()
    mainloop()
    log.error('Main thread ended, stopping updater...')
    updater.stop()
  except Exception as e:
    updater.stop()
    log.error((traceback.format_exc()))
