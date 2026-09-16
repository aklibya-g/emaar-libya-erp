import os
os.environ['FLASK_APP'] = 'src.web.app:create_app'
os.chdir('E:/EmarrCoSys')

from src.web.app import create_app
app = create_app()
app.run(host='127.0.0.1', port=5000, debug=False)
