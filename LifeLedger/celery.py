# LifeLedger/LifeLedger/celery.py
import os
import logging
import sys

# --- Gevent Monkey Patching ---
# Apply this at the VERY TOP of the file, before any other imports,
# especially before 'from celery import Celery'.
# This is crucial for the gevent worker pool.
_IS_GEVENT_WORKER = False
# Check if 'celery' command is being run and if '-P gevent' or '--pool=gevent' is an argument
if 'celery' in os.path.basename(sys.argv[0]) and len(sys.argv) > 1: # Check sys.argv length too
    if any(arg == '-P' and i + 1 < len(sys.argv) and sys.argv[i+1] == 'gevent' for i, arg in enumerate(sys.argv)) or \
       any(arg.startswith('--pool=gevent') for arg in sys.argv):
        _IS_GEVENT_WORKER = True

if _IS_GEVENT_WORKER:
    try:
        from gevent import monkey
        monkey.patch_all()
        print("Gevent monkey patching applied at the top of celery.py (detected gevent worker).")
    except ImportError:
        print("WARNING: gevent not found, monkey patching in celery.py skipped.")
# --- End Gevent Monkey Patching ---

from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LifeLedger.settings')

app = Celery('LifeLedger')

# Use a string here so the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   in settings.py should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Set default queue, exchange, and routing key from settings if they exist,
# otherwise use Celery's default 'celery' queue name.
# This helps ensure tasks go to the intended queue if not specified explicitly at the task level.
app.conf.update(
    task_default_queue = getattr(settings, 'CELERY_TASK_DEFAULT_QUEUE', 'celery'),
    task_default_exchange = getattr(settings, 'CELERY_TASK_DEFAULT_EXCHANGE', 
                                    getattr(settings, 'CELERY_TASK_DEFAULT_QUEUE', 'celery')),
    task_default_routing_key = getattr(settings, 'CELERY_TASK_DEFAULT_ROUTING_KEY', 
                                       getattr(settings, 'CELERY_TASK_DEFAULT_QUEUE', 'celery')),
)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks() 

# This is the debug task defined in your project's celery.py
@app.task(bind=True, ignore_result=True, name='LifeLedger.celery.debug_task_explicit')
def debug_task(self):
    """
    A simple debug task that prints its request info.
    Explicitly named for clarity in debugging.
    """
    task_logger = logging.getLogger(self.name) # Use task name for logger
    task_logger.info(f"--- {self.name} RECEIVED --- Request: {self.request!r}")
    print(f"--- PRINT: {self.name} RECEIVED --- Request: {self.request!r}")
    return f"Celery task {self.name} executed successfully!"
