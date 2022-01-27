import time

def get_temp_vars():
  return {
      'state':'main_menu',
      'desired_task':None,
      'timer_message':None,
      'timer_start':None,
      'stats_delta':0,
      }

def get_default_user(tg_username):
  return {
      'username':tg_username,
      'timezone':None,
      'last_task_end_time':int(time.time()),
      'active_task':{},
      'tasks':{},
      'stats_type':'alltime',
      }

def get_default_task():
  return {
      'enabled': True,
      'date_added': int(time.time()),
      'time_total': 0,
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
      '-5m',
      '-10m',
      '-20m',
      '-30m',
      '-1h',
      '-2h',
      ]
