import time

def get_temp_vars():
  return {
      'desired_task':None,
      'timer_message':None,
      'timer_start':None,
      }

def get_default_user(tg_username):
  return {
      'username':tg_username,
      'timezone':None,
      'state':'main_menu',
      'last_task_end_time':int(time.time()),
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
      'history':[],
      }

def get_name(name):
  names = {
    'disable_menu':'Hide menu',
    'start_task':'Start task',
    'add_task':'Add task',
    'remove_task':'Remove task',
    'stop':'Stop ',
    'task_stats':'Show task stats',
    'set_timezone':'Set timezone',
    'now':'Now',
    }
  return names[name]

def get_time_presets():
  return [
      '5m',
      '10m',
      '20m',
      '30m',
      '1h',
      '2h',
      ]
