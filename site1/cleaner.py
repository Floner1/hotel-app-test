import re
import sys

with open('home/views.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'_CONTENT_DEFAULTS\s*=\s*{.*?}', '', text, flags=re.DOTALL)
text = re.sub(r'def _get_content.*?except Exception:\s*return default', '', text, flags=re.DOTALL)
text = re.sub(r'def _get_all_content.*?except Exception:\s*return dict\(defaults\)', '', text, flags=re.DOTALL)
text = re.sub(r"'ct':\s*_get_all_content\(_CONTENT_DEFAULTS\),?\s*", '', text)

with open('home/views.py', 'w', encoding='utf-8') as f:
    f.write(text.strip() + '\n')
print("Cleaned!")
