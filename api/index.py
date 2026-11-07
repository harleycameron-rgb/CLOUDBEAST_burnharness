"""Vercel WSGI entrypoint; application work retains the existing runtime guard."""
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.preview import app
