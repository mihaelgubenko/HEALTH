#!/usr/bin/env python
import os
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')
    django.setup()
    execute_from_command_line(['manage.py', 'migrate'])
