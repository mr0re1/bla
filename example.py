from core import  Variables
from proof import proof

# Declare domain - the set of variables used in the program
D = Variables("Vars", ["A_set", "A_get"])

# The client, that `db.write(A, true)" to DB 
# and expects "db.read(A) = true"
def client():
    A_set = True
    assert A_get == True

# Eventually consistent DB
def server():
    "begin" # while True
    A_get = A_set
    if True: "begin"

# Proof that assertion holds
proof([client, server], D)
# Spoiler: it doesn't


    



