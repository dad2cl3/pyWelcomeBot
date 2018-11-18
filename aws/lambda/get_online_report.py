import json, os, redis

io_cache = redis.StrictRedis (
    host=os.environ['redis_cache_host'],
    port=os.environ['redis_cache_port'],
    password=os.environ['redis_cache_password']
)

def handler (event, context):
    redis_key = os.environ['redis_key']

    online_report = io_cache.hget(redis_key, 'json')
    online_report = json.loads(online_report.decode('UTF-8'))

    return online_report