import time
import icalendar
import uuid

def get_temp_vars():
  return {
      'state':'main_menu',
      'menu_state':'menu_main',
      'timer_message':None,
      'task_start':None,
      'task_name':None,
      'task_description':None,
      'context_start':None,
      'context_name':None,
      'context_description':None,
      'stats_delta':0,
      'stats_info':'tasks',
      'stats_sort':'by-entry',
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
      'last_context_end_time':int(time.time()),
      'active_context':{},
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
      'last_active': None,
      'time_total': 0,
      'descriptions':[],
      'tags':[],
      }

def get_default_place(name):
  return {
      'name': name,
      'enabled': True,
      'date_added': int(time.time()),
      'last_active': None,
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
    'get_timer':'Timer',

    'menu_main':'Main',
    'menu_ext':'Ext',
    'menu_stats':'Stats',
    'menu_edit':'Editing',
    'menu_settings':'Settings',
    'menu_edit_tasks':'Edit tasks',
    'menu_edit_places':'Edit places',
    'menu_edit_tags':'Edit tags',

    'stop':'Stop ',
    'now':'Now',
    'show_disabled':'Show disabled',
    'show_enabled':'Show enabled',

    'entry_stats':'Total statistics',
    'entry_info':'Entry info',

    'start_task':'Start task',
    'add_task':'Add task',
    'remove_task':'Disable task',
    'enable_task':'Enable task',
    'task_tags':'Task tags',
    'task_description': 'Task description',

    'change_context':'Context: ',
    'no_context':'No context',
    'context_description': 'Context description',

    'change_place':'Place: ',
    'add_place':'Add place',
    'disable_place':'Disable place',
    'enable_place':'Enable place',
    'place_tags':'Place tags',

    'add_tag':'Add tag',
    'disable_tag':'Disable tag',
    'enable_tag':'Enable tag',
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
