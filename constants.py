import time
import icalendar
import uuid

def get_temp_vars():
  return {
      'state':'main_menu',
      'menu_state':'menu_main',
      'task_name':None,
      'task_description':None,
      'timer_message':None,
      'timer_start':None,
      'stats_delta':0,
      'stats_info':'tasks',
      'place_name':None,
      'tag_editor_entry_id':None,
      'tag_editor_active_tags':[],
      }

def get_default_user(tg_username):
  return {
      'username':tg_username,
      'timezone':None,
      'last_task_end_time':int(time.time()),
      'active_task':{},
      'last_place_end_time':int(time.time()),
      'active_place':{},
      'stats_type':'detailed',
      'web_key':None,
      'tasks':{},
      'places':{},
      'tags':{
        str(uuid.uuid4()):get_default_tag('context', ['context',]),
        },
      }

def get_default_task(name):
  return {
      'name': name,
      'enabled': True,
      'date_added': int(time.time()),
      'time_total': 0,
      'descriptions':[],
      'tags':[],
      }

def get_default_place(name):
  return {
      'name': name,
      'enabled': True,
      'date_added': int(time.time()),
      'time_total': 0,
      'tags':[],
      }

def get_default_tag(name, functions=['tag',]):
  return {
      'name': name,
      'enabled': True,
      'functions':functions,
      'date_added': int(time.time()),
      }

def get_tag_functions():
  return [
      'tag',
      'context',
      ]

def get_default_list_task(task_id, description, timezone, start_time, end_time):
  return {
      'id': task_id,
      'timezone': timezone,
      'start': start_time,
      'end': end_time,
      'description': description,
      }

def get_default_place_task(place_id, timezone, start_time, end_time):
  return {
      'id': place_id,
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
    'set_timezone':'Set timezone',
    'menu_main':'Main menu',
    'menu_edit':'Editing menu',
    'menu_settings':'Settings',
    'task_stats':'Show stats',

    'start_task':'Start task',
    'add_task':'Add task',
    'remove_task':'Disable task',
    'enable_task':'Enable task',
    'change_description': 'Change description',

    'stop':'Stop ',
    'now':'Now',
    'show_disabled':'Show disabled',
    'show_enabled':'Show enabled',

    'change_place':'Place: ',
    'add_place':'Add place',
    'disable_place':'Disable place',
    'enable_place':'Enable place',

    'add_tag':'Add tag',
    'disable_tag':'Disable tag',
    'enable_tag':'Enable tag',
    'task_tags':'Task tags',
    'place_tags':'Place tags',
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
