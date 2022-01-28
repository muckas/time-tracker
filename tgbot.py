import os
import time
import logging
from contextlib import suppress
import telegram
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import telegram.ext
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import db
import logic
import constants

log = logging.getLogger('main')

tg = None

help_text = '''I am sorry, but there's nothing I can help you with...'''

def send_message(user_id, text, silent=True, keyboard=None, reply_markup=None):
  users = db.read('users')
  username = users[user_id]['username']
  if keyboard != None:
    if keyboard == []:
      reply_markup = ReplyKeyboardRemove()
    else:
      reply_markup = ReplyKeyboardMarkup(keyboard)
  message = tg.send_message(chat_id=user_id, text=text, disable_notification=silent, reply_markup=reply_markup)
  log.info(f'Message to @{username}({user_id}):{text}')
  return message

def send_document(user_id, file_path, file_name, caption=None, silent=True):
  try:
    tg.send_chat_action(chat_id=user_id, action=telegram.ChatAction.UPLOAD_DOCUMENT)
    with open(file_path, 'rb') as file:
      tg.send_document(chat_id=user_id, document=file, filename=file_name, caption=caption, disable_notification=silent)
      return True
  except FileNotFoundError:
    return False

def log_message(update):
  user_id = str(update.message.chat['id'])
  username = str(update.message.chat['username'])
  text = update.message.text
  log.info(f'Message from @{username}({user_id}):{text}')

def add_user_to_db(update):
  user_id = str(update.message.chat['id'])
  log.info(f'Adding new user {user_id} to database')
  users = db.read('users')
  tg_username = str(update.message.chat['username'])
  users.update({user_id:constants.get_default_user(tg_username)})
  db.write('users', users)
  with suppress(FileExistsError):
    path = os.path.join('db', 'data', user_id)
    os.makedirs(path)
    log.info(f'Created {path} folder')
  log.info(f'Added @{tg_username} to database')

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
        send_message(user_id, f"Your id is {user_id}")
      return False
  else:
    return True

def message_handler(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  if validated(update):
    text = update.message.text
    logic.check_temp_vars(user_id)
    logic.menu_handler(user_id, text)

def command_start(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  if validated(update):
    logic.check_temp_vars(user_id)
    logic.enable_menu(users, user_id)

def command_help(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  if validated(update, notify=True):
    send_message(user_id, help_text, silent=True)

def command_menu(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  users = db.read('users')
  if validated(update):
    logic.check_temp_vars(user_id)
    logic.enable_menu(users, user_id)

def command_timer(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  if validated(update):
    logic.check_temp_vars(user_id)
    logic.get_new_timer(user_id)

def command_calendar(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  logic.send_calendar(user_id)

def callback_handler(update, context):
  users = db.read('users')
  query = update.callback_query
  user_id = str(query.message.chat_id)
  logic.check_temp_vars(user_id)
  function, option = query.data.split(':')
  if function == 'task_stats':
    report, reply_markup = logic.get_task_stats(users, user_id, option)
    with suppress(telegram.error.BadRequest):
      query.edit_message_text(text=report, reply_markup=reply_markup)
  query.answer()

def error_handler(update, context):
  log.warning(msg="Exception while handling an update:", exc_info=context.error)

def start(tg_token):
  log.info('Starting telegram bot...')
  updater = telegram.ext.Updater(tg_token)
  dispatcher = updater.dispatcher
  dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
  dispatcher.add_handler(CommandHandler('start', command_start))
  dispatcher.add_handler(CommandHandler('help', command_help))
  dispatcher.add_handler(CommandHandler('menu', command_menu))
  dispatcher.add_handler(CommandHandler('cancel', command_menu))
  dispatcher.add_handler(CommandHandler('timer', command_timer))
  dispatcher.add_handler(CommandHandler('calendar', command_calendar))
  dispatcher.add_handler(CallbackQueryHandler(callback_handler))
  dispatcher.add_error_handler(error_handler)
  updater.start_polling()
  log.info('Telegram bot started')
  return updater
