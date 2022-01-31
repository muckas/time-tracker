import time
import icalendar

def get_temp_vars():
  return {
      'state':'main_menu',
      'task_name':None,
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
      'web_key':None,
      }

def get_default_task(name):
  return {
      'name': name,
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
      'tasks':[],
      }

def get_default_list_task(task_id, timezone, start_time, end_time):
  return {
      'id': task_id,
      'timezone': timezone,
      'start': start_time,
      'end': end_time,
      }

def get_new_calendar(name, timezone):
  cal = icalendar.Calendar()
  cal.add('X-WR-CALNAME', name)
  cal.add('TZOFFSET', timezone)
  return cal

def get_name(name):
  names = {
    'disable_menu':'Hide menu',
    'start_task':'Start task',
    'add_task':'Add task',
    'remove_task':'Disable task',
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
