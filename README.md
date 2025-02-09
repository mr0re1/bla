# If TLA+ is too hard

[TLA+](https://lamport.azurewebsites.net/tla/tla.html) is awesome but hard. <br>
**bla** is small proofer that uses Python syntax.

Declare set of programs that share a common memory but run on different clocks.
Verify that assertions always hold true, no matter the order of execution.

```py
# examples/inconsistency.py

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
        "A_set": False,
        "A_get": False,
    },
)
# Spoiler: it doesn't
```

```sh
$ python examples/inconsistency.py
----- step #0:
 def client():            | def server():         | A_set=False
 ->  A_set = True         | ->  while True:       | A_get=False
     assert A_get == True |         A_get = A_set |

----- step #1:
 def client():            | def server():         | A_set=False
 ->  A_set = True         |     while True:       | A_get=False
     assert A_get == True | ->      A_get = A_set |

----- step #2:
 def client():            | def server():         | A_set=False
 ->  A_set = True         | ->  while True:       | A_get=False
     assert A_get == True |         A_get = A_set |

----- step #3:
 def client():            | def server():         | A_set=True
     A_set = True         | ->  while True:       | A_get=False
 ->  assert A_get == True |         A_get = A_set |

Assertion failed: assert A_get == True
```
