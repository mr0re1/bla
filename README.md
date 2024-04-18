# Dummy "TLA"

Declare set of programs that share a common memory but run on differnt clocks.
Verify that assertions always hold true, no matter the order of execution.

```py
# example.py

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

# Proof that assertion always holds
proof([client, server], D)
# Spoiler: it doesn't
```

```sh
$ python3 example.py
----- step #0:
 def client():            | def server():            | A_set=False
 ->  A_set = True         |     "begin" # while True | A_get=False
     assert A_get == True | ->  A_get = A_set        |
                          |     if True: "begin"     |


----- step #1:
 def client():            | def server():            | A_set=False
 ->  A_set = True         |     "begin" # while True | A_get=False
     assert A_get == True |     A_get = A_set        |
                          | ->  if True: "begin"     |


----- step #2:
 def client():            | def server():            | A_set=True
     A_set = True         |     "begin" # while True | A_get=False
     assert A_get == True |     A_get = A_set        |
 ->==HALTED==             | ->  if True: "begin"     |


Assertion failed: client:1: assert A_get == True
```