from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import logging

logging.getLogger("watchdog").setLevel(logging.WARNING)

class ConfFileHandler(PatternMatchingEventHandler):
	def __init__(self, callback, file):
		super(ConfFileHandler, self).__init__(None, None, True, False)
		self.callback = callback
		self.file = file

	def dispatch(self, event):
		#print(event.event_type, event.is_directory, event.src_path)
		if event.src_path == self.file and event.event_type == 'modified':
			self.callback()

def setObserver(callback, file_name, file_path):
	observer = Observer()
	observer.schedule(ConfFileHandler(callback, file_name), path=file_path)
	observer.start()