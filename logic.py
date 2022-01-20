import logging
import db
import tgbot
import constants

log = logging.getLogger('main')

def get_main_menu(user_id):
  users = db.read('users')
  active_task = users[user_id]['active_task']
  if active_task:
    start_task_button = f'{constants.get_name("stop")}{active_task["name"]}'
  else:
    start_task_button = constants.get_name('start_task')
  keyboard = [
      [start_task_button],
      [constants.get_name('add_task'), constants.get_name('remove_task')],
      # [constants.get_name('disable_menu')]
      ]
  return keyboard

def enable_menu(user_id):
  change_state(user_id, 'main_menu')
  tgbot.send_message(user_id, 'Main menu', keyboard=get_main_menu(user_id))

def disable_menu(user_id):
  tgbot.send_message(user_id, 'Menu disabled', keyboard=[])

def change_state(user_id, new_state):
  users = db.read('users')
  users[user_id]['state'] = new_state
  db.write('users', users)

def get_list_of_tasks(user_id):
  users = db.read('users')
  return users[user_id]['tasks']

def menu_handler(user_id, text):
  users = db.read('users')
  state = users[user_id]['state']

  # STATE - main_menu
  if state == 'main_menu':
    button_name = text

    if button_name == constants.get_name('disable_menu'):
      disable_menu(user_id)

    elif button_name == constants.get_name('start_task'):
      tasks = get_list_of_tasks(user_id)
      if tasks:
        keyboard = []
        for task in tasks.keys():
          keyboard.append([task])
        tgbot.send_message(user_id, 'Choose a task to start\n/cancel', keyboard=keyboard)
        change_state(user_id, 'start_task')
      else:
        tgbot.send_message(user_id, "You don't have any tasks")

    elif button_name == constants.get_name('add_task'):
      tgbot.send_message(user_id, 'Name a task\n/cancel', keyboard = [])
      change_state(user_id, 'add_task')

    elif button_name == constants.get_name('remove_task'):
      tasks = get_list_of_tasks(user_id)
      if tasks:
        keyboard = []
        for task in tasks.keys():
          keyboard.append([task])
        tgbot.send_message(user_id, 'Choose a task to remove\n/cancel', keyboard=keyboard)
        change_state(user_id, 'remove_task')
      else:
        tgbot.send_message(user_id, "You don't have any tasks")

    else: # Checking for "Stop {task}"
      stop_string = constants.get_name('stop')
      stop_string_len = len(stop_string)
      if button_name[:stop_string_len] == stop_string:
        task_name = button_name[stop_string_len:]
        users[user_id]['active_task'] = None
        db.write('users',users)
        tgbot.send_message(user_id, f'Stopped {task_name}', keyboard=get_main_menu(user_id))

  # STATE - start_task
  elif state == 'start_task':
    task_name = text
    users[user_id]['active_task'] = {
        'name': task_name,
        }
    db.write('users',users)
    tgbot.send_message(user_id, f'Started {task_name}', keyboard=get_main_menu(user_id))
    change_state(user_id, 'main_menu')

  # STATE - add_task
  elif state == 'add_task':
    task_name = text
    if task_name in users[user_id]['tasks'].keys():
      tgbot.send_message(user_id, f'Task "{task_name}" already exists\nChoose another name\n/cancel')
    else:
      users[user_id]['tasks'].update(
          {task_name:{}}
          )
      db.write('users', users)
      tgbot.send_message(user_id, f'Added task "{task_name}"', keyboard=get_main_menu(user_id))
      change_state(user_id, 'main_menu')

  # STATE - remove_task
  elif state == 'remove_task':
    task_name = text
    if users[user_id]['active_task'] == task_name:
      users[user_id]['active_task'] = None
    if task_name in users[user_id]['tasks'].keys():
      users[user_id]['tasks'].pop(task_name)
      db.write('users',users)
      tgbot.send_message(user_id, f'Removed task "{task_name}"', keyboard=get_main_menu(user_id))
    else:
      tgbot.send_message(user_id, f'Task "{task_name}" doesn\'t exist', keyboard=get_main_menu(user_id))
    change_state(user_id, 'main_menu')
