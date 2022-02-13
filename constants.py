import time
import icalendar
import uuid

def get_temp_vars():
  return {
      'state':'main_menu',
      'menu_state':'menu_main',
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
      'stats_type':'detailed',
      'web_key':None,
      }

def get_default_task(name):
  return {
      'name': name,
      'enabled': True,
      'date_added': int(time.time()),
      'time_total': 0,
      'descriptions':[],
      }

def get_default_list_task(task_id, description, timezone, start_time, end_time, ):
  return {
      'id': task_id,
      'timezone': timezone,
      'start': start_time,
      'end': end_time,
      'description': description,
      }

def get_new_calendar(name, timezone):
  cal = icalendar.Calendar()
  cal.add('X-WR-CALNAME', name)
  cal.add('TZOFFSET', timezone)
  return cal

def get_name(name):
  names = {
    'disable_menu':'Hide menu',
    'menu_main':'Main menu',
    'menu_settings':'Settings',
    'start_task':'Start task',
    'add_task':'Add task',
    'remove_task':'Disable task',
    'enable_task':'Enable task',
    'stop':'Stop ',
    'task_stats':'Show task stats',
    'set_timezone':'Set timezone',
    'now':'Now',
    'show_disabled':'Show disabled tasks',
    'show_enabled':'Show enabled tasks',
    'change_description': 'Change description',
    }
  return names[name]

def get_time_presets():
  return [
      '-5m',
      '-10m',
      '-15m',
      '-20m',
      '-25m',
      '-30m',
      '-1h',
      '-1d',
      ]
