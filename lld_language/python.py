# ds - dict
# loops

from collections import defaultdict, Counter

l = []
l = [True]*9
l = [1]*10

# 1 - iterate items
for i in l :
    print(i)
    
# 2 - 0 to n=10
for i in range(10):
    ...

# 3- s=1 to e=10
for i in range(1,10):
    ...

# 4 s=0, e=len(l), step=2 ie i+=2
for i in range(0,len(l),2):
    ...

# 5 i = idx, val = val
for i,val in enumerate(l):
    ...

# enumerate(l) = [1,2,3,4] => [(0,1), (1,2), (2,3),(3,4)]

# 6 - unpacking values
i,j,k,l = ("sid","kriti","mansi","aditi") 

l = [1,2,3,4,5]

if 5 in l:
    print("5 is present")

l.append(6)
l.reverse()

# =========================================================

# normal dict
d = {}
d['1']=1. # assign
d['2'] # throws KeyError
d.get('2') # doesnt throw exception, returns None

if '2' in d:
    print("yay")

# dont have to worry about missing keys
dd = defaultdict(int)
dd = defaultdict(lambda: {"name": "","age":18,"marks": 100})

# lambda
y = lambda x : x**2

y(2) # 4
# {
#     "kritika" : {
#         "name": "",
#         "age":18,
#         "marks": 100
#     },
#     "sid" : {
#         "name": "",
#         "age":18,
#         "marks": 100
#     }
# }

for i in d:
    print(i)

for k in d.keys():
    print(k)

for i in d.items():
    print(i)

for k,v in d.items():
    print(f'{k}------->{v}')

for v in d.values():
    print(v)

for i,item in enumerate(d.items()):
    print(f'{i} : {item}')

if key in d:
    return True


# parsing
import csv
import io

x = input()
"c1,c2,c3,c4,"
"v1,v2,"

reader = csv.DictReader(io.StringIO(x))

for txn in reader:
    # txn_id, m_id, amount, status 
    txn["txn_id"]

# math
import math

# string handling


# lambdas, comprehensions

# sorting - comparator: klists and dict

# datetime