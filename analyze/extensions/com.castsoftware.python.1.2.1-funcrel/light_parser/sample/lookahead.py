'''
Created on 12 nov. 2014

@author: MRO
'''
from light_parser import Lookahead

stream = [1, 2, 3, 4]

stream = Lookahead(stream)

i = iter(stream)

print(i.__next__())

i.start_lookahead()

print(i.__next__())

i.stop_lookahead()

print(i.__next__())


print('\n      '.isspace())