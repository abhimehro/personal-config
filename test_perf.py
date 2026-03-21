import timeit
setup = """
l = list(range(1000000))
with open('test.txt', 'w') as f:
    pass
"""
t1 = timeit.timeit("with open('test.txt', 'w') as f:\n for i in l:\n  f.write(f'{i}\\n')", setup=setup, number=10)
t2 = timeit.timeit("with open('test.txt', 'w') as f:\n f.writelines(f'{i}\\n' for i in l)", setup=setup, number=10)

print(f"write loop: {t1}")
print(f"writelines gen: {t2}")

setup2 = """
d = {i: i for i in range(100000)}
"""

t3 = timeit.timeit("list(d.keys())", setup=setup2, number=1000)
t4 = timeit.timeit("list(d)", setup=setup2, number=1000)

print(f"list(d.keys()): {t3}")
print(f"list(d): {t4}")
