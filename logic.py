import logging
import db
import tgbot
import naming

log = logging.getLogger('main')

def get_main_menu(user_id):
  users = db.read('users')
  active_task = users[user_id]['active_task']
  if active_task:
    start_task_button = f'{naming.menu("stop")}{active_task}'
  else:
    start_task_button = naming.menu('start_task')
  keyboard = [
      [start_task_button],
      [naming.menu('add_task'), naming.menu('remove_task')],
      [naming.menu('disable_menu')]
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

    if button_name == naming.menu('disable_menu'):
      disable_menu(user_id)

    elif button_name == naming.menu('start_task'):
      tasks = get_list_of_tasks(user_id)
      if tasks:
        keyboard = []
        for task in tasks:
          keyboard.append([task])
        tgbot.send_message(user_id, 'Choose a task to start', keyboard=keyboard)
        change_state(user_id, 'start_task')
      else:
        tgbot.send_message(user_id, "You don't have any tasks")

    elif button_name == naming.menu('add_task'):
      tgbot.send_message(user_id, 'Name a task', keyboard = [])
      change_state(user_id, 'add_task')

    elif button_name == naming.menu('remove_task'):
      tasks = get_list_of_tasks(user_id)
      if tasks:
        keyboard = []
        for task in tasks:
          keyboard.append([task])
        tgbot.send_message(user_id, 'Choose a task to remove', keyboard=keyboard)
        change_state(user_id, 'remove_task')
      else:
        tgbot.send_message(user_id, "You don't have any tasks")

  # STATE - start_task
  elif state == 'start_task':
    task_name = text
    users[user_id]['active_task'] = task_name
    db.write('users',users)
    change_state(user_id, 'main_menu')
    tgbot.send_message(user_id, f'Started {task_name}', keyboard=get_main_menu(user_id))

  # STATE - add_task
  elif state == 'add_task':
    task_name = text
    users[user_id]['tasks'].append(task_name)
    db.write('users', users)
    change_state(user_id, 'main_menu')
    tgbot.send_message(user_id, f'Added task "{task_name}"', keyboard=get_main_menu(user_id))
