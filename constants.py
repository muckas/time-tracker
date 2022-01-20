def get_default_user(tg_username):
  return {
      'username':tg_username,
      'timezone':None,
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
    'stop':'Stop ',
    'task_stats':'Show task stats',
    'set_timezone':'Set timezone'
    }
  return names[name]
