"""Exercise every adapter with a synthetic profile during deployment builds."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from portal.catalog import MODULES
from portal.views import execute

profile = {'age':35,'education':'HS-grad','education_num':9,'workclass':'Private','occupation':'Sales','marital_status':'Never-married','relationship':'Not-in-family','hours_per_week':40,'capital_gain':0,'capital_loss':0,'income':'<=50K','native_us':'1','race':'White','sex':'Male','native_country':'United-States'}
for module in MODULES:
    result = execute(module, {field.key: profile[field.key] for field in module.fields})
    if not result.get('label'):
        raise SystemExit(f'{module.slug}: missing result')
    print(f'{module.slug}: prediction OK')
