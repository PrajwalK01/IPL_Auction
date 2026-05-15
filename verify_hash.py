from werkzeug.security import check_password_hash

h = "scrypt:32768:8:1$o333lkByKrM5Dawt$3447822a8bd76acbe90f062145226986d57cd5e8161d60d238b6954601e37847353cb72ed39e882e73318588285b9f18afacd1d8db074f67a1a40cc8d7877c89"
p = "admin123"

print(f"Checking hash for {p}: {check_password_hash(h, p)}")
