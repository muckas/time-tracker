def get_default_user(tg_username):
  return {
      'username':tg_username,
      'timezone':None,
      'state':'main_menu',
      'last_task_end_time':0,
      'active_task':{},
      'tasks':{},
      }

def get_defaul_diary():
  return {
      'tasks_total':{},
      'days':{},
      }

def get_default_day(timezone):
  return {
      'timezone':timezone,
      'tasks_total':{},
      'history':[]
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
