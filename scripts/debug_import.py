print('start');
print('about to import app');
from app import app
print('imported app');
print('about to import routes.admin_routes');
import importlib
try:
    ar = importlib.import_module('routes.admin_routes')
    print('imported routes.admin_routes OK')
except Exception as e:
    print('import failed:')
    import traceback; traceback.print_exc()
print('done')
