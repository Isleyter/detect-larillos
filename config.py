# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
    MONGODB_SETTINGS = {
        'host': os.environ.get('MONGODB_URI')
    }
    
#class Config:
 #   SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
  #  MONGODB_SETTINGS = {
   #     'db': 'data',
    #    'host': 'localhost',
     #   'port': 27017
    #}
    
