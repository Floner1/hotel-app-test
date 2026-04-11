import os, django, re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()
from django.db import connection

sql_file = r'D:\School work\hotel booking webapp project\hotel-app-test\tables v6 for hotel.sql'
with open(sql_file, 'r', encoding='utf-8') as f:
    sql = f.read()

batches = re.split(r'(?i)^\s*GO\s*$', sql, flags=re.MULTILINE)

try:
    with connection.cursor() as cursor:
        for batch in batches:
            b = batch.strip()
            if b and not b.lower().startswith('use '):
                try:
                    cursor.execute(b)
                except Exception as e:
                    print('Error executing batch:', b[:100], '\nError:', e)
                    raise
    print('Database script executed successfully!')
except Exception as e:
    print('Fatal Error:', e)
