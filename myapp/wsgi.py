"""
WSGI config for myapp project (Optimized for Vercel & Production)
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myapp.settings')

application = get_wsgi_application()

# Vercel entrypoint alias
app = application
