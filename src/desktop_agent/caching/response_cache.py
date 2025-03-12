from datetime import datetime, timedelta

class ResponseCache:
    def __init__(self, expiration_minutes=5):
        self.cache = {}
        self.expiration = timedelta(minutes=expiration_minutes)
    
    def get(self, key):
        entry = self.cache.get(key)
        if entry and datetime.now() < entry['expires']:
            return entry['value']
        return None
    
    def set(self, key, value):
        self.cache[key] = {
            'value': value,
            'expires': datetime.now() + self.expiration
        }
        return True 