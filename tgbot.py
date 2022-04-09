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
  if keyboard != None:
    if keyboard == []:
      reply_markup = ReplyKeyboardRemove()
    else:
      reply_markup = ReplyKeyboardMarkup(keyboard)
  emoji = ''
  if logic.temp_vars[user_id]['task_start']:
    emoji += '\U0001F534 '
  if logic.temp_vars[user_id]['context_start']:
    emoji += '\U00002b55 '
  text = emoji + text
  message = tg.send_message(chat_id=user_id, text=text, disable_notification=silent, reply_markup=reply_markup)
  log.info(f'Message to user {user_id}:{text}')
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

def command_link(update, context):
  log_message(update)
  users = db.read('users')
  user_id = str(update.message.chat['id'])
  try:
    text = update.message.text.split(' ', 1)[1]
    logic.generate_new_key(users, user_id, text)
  except IndexError:
    logic.send_links(users, user_id)

def callback_handler(update, context):
  users = db.read('users')
  query = update.callback_query
  user_id = str(query.message.chat_id)
  log.info(f'Query from user {user_id}: {query.data}')
  logic.check_temp_vars(user_id)
  function, option = query.data.split(':')
  if function == 'stats':
    text, reply_markup = logic.handle_stats_query(users, user_id, option)
  elif function == 'info':
    text, reply_markup = logic.handle_info_query(users, user_id, option)
  elif function == 'desc_info':
    text, reply_markup = logic.handle_description_info_query(users, user_id, option)
  elif function == 'description':
    text, reply_markup = logic.handle_description_query(users, user_id, option)
  elif function == 'tag':
    text, reply_markup = logic.handle_tags_query(users, user_id, option)
  elif function == 'order':
    text, reply_markup = logic.handle_order_editor_query(users, user_id, option)
  elif function == 'options':
    text, reply_markup = logic.handle_options_editor_query(users, user_id, option)
  else:
    text = 'Error'
    reply_markup = None
  with suppress(telegram.error.BadRequest):
    query.edit_message_text(text=text, reply_markup=reply_markup)
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
  dispatcher.add_handler(CommandHandler('link', command_link))
  dispatcher.add_handler(CallbackQueryHandler(callback_handler))
  dispatcher.add_error_handler(error_handler)
  updater.start_polling()
  log.info('Telegram bot started')
  return updater
