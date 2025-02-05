import sys

sys.path.insert(0, "../bla")

from bla import proof

# The client, that `db.write(A, true)" to DB
# and expects "db.read(A) = true"
def client():
    A_set = True
    assert A_get == True


# Eventually consistent DB
def server():
    while True:
        A_get = A_set


# Proof that assertion holds
proof(
    [client, server],
    {
        "A_set": bool,
        "A_get": bool,
    },
)
# Spoiler: it doesn't
