"""One process avoids duplicating the team's large model cache."""
import os
bind = '0.0.0.0:' + os.getenv('PORT', '8000')
workers = 1
worker_class = 'sync'
threads = 1
timeout = 120
graceful_timeout = 30
accesslog = '-'
errorlog = '-'
capture_output = True
# Do not automatically scale workers with CPU count: each loads the models.
