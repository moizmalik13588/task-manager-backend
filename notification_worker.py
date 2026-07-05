import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
pubsub = r.pubsub()
pubsub.psubscribe("user_notifications:*")

print("Notification worker started, listening...")

for message in pubsub.listen():
    if message['type'] == 'pmessage':
        channel = message['channel']
        data = message['data']
        print(f"[NOTIFICATION] {channel} -> {data}")