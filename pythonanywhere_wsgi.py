import os
import sys

# Add project directory to path
project_home = os.path.expanduser('~/emaar-libya-erp')
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['FLASK_APP'] = 'src.web.app:create_app'

from src.web.app import create_app
application = create_app()
