import logging
import traceback
import os
import sys
import datetime
import http.server
import socketserver
from contextlib import suppress
import db

def get_user_by_web_key(key):
  users = db.read('users')
  for user_id in users:
    if users[user_id]['web_key'] == key:
      return user_id
  return None

class RequestHandler(http.server.SimpleHTTPRequestHandler):
  def do_GET(self):
    log.debug(f'GET {self.path}')
    url_path = self.path.split('/')
    if url_path[-1] == '': url_path.pop(-1)
    if url_path[-1] == 'tasks.ics':
      user_id = get_user_by_web_key(url_path[-2])
      if user_id:
        file_path = os.path.join('db', 'data', user_id, f'tasks-calendar-{user_id}.ics')
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.end_headers()
        with open(file_path, 'rb') as file:
          self.wfile.write(bytes(file.read()))
        return
    elif url_path[-1] == 'places.ics':
      user_id = get_user_by_web_key(url_path[-2])
      if user_id:
        file_path = os.path.join('db', 'data', user_id, f'places-calendar-{user_id}.ics')
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.end_headers()
        with open(file_path, 'rb') as file:
          self.wfile.write(bytes(file.read()))
        return
    html = 'Incorrect request, use /link to get valid links'
    self.wfile.write(bytes(html, 'utf8'))
    return

if __name__ == '__main__':
  # Logger setup
  with suppress(FileExistsError):
    os.makedirs('logs')
    print('Created logs folder')

  log = logging.getLogger('')
  log.setLevel(logging.DEBUG)

  filename = 'webserver-' + datetime.datetime.now().strftime('%Y-%m-%d') + '.log'
  file = logging.FileHandler(os.path.join('logs', filename))
  file.setLevel(logging.DEBUG)
  fileformat = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
  file.setFormatter(fileformat)
  log.addHandler(file)

  stream = logging.StreamHandler()
  stream.setLevel(logging.DEBUG)
  streamformat = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
  stream.setFormatter(fileformat)
  log.addHandler(stream)
  # End of logger setup

  log.info('=====================================')
  log.info('Task Tracker Webserver start')
  try:
    PORT = db.read('params')['web_port']
    handler = RequestHandler

    httpd = socketserver.TCPServer(('', PORT), handler)
    log.info(f'Server started on localhost at port {PORT}')
    httpd.serve_forever()
  except Exception as e:
    log.error((traceback.format_exc()))
    log.info(f'Stopping server')
    httpd.shutdown()
    httpd.server_close()
    sys.exit(2)
