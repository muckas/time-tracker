import os
import logging
import telegram
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import telegram.ext
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import db

log = logging.getLogger('main')

tg = None

help_text = '''I am sorry, but there's nothing I can help you with...'''

def send_message(user_id, text, silent=False, reply_markup=None):
  users = db.read('users')
  username = users[user_id]['username']
  tg.send_message(chat_id=user_id, text=text, disable_notification=silent, reply_markup=reply_markup)
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
    if text == 'Remove Keyboard':
      send_message(user_id, 'Keyboard Removed', reply_markup=ReplyKeyboardRemove())

def command_start(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  if validated(update):
    send_message(user_id, help_text)

def command_help(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  if validated(update, notify=True):
    send_message(user_id, help_text)

def command_menu(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  if validated(update):
    keyboard = [
        ['Start task'],
        ['Edit tasks'],
        ['Remove Keyboard']
        ]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    send_message(user_id, 'Main menu', reply_markup=reply_markup)

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
  dispatcher.add_error_handler(error_handler)
  updater.start_polling()
  log.info('Telegram bot started')
  return updater
