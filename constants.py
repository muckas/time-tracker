def get_default_user(tg_username):
  return {
      'username':tg_username,
      'state':'main_menu',
      'active_task':{},
      'tasks':{},
      }

def get_name(name):
  names = {
    'disable_menu':'Hide menu',
    'start_task':'Start task',
    'add_task':'Add task',
    'remove_task':'Remove task',
    'stop':'Stop '
    }
  return names[name]
