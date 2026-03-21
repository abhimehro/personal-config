import timeit
import json
setup = """
domains = ["test" + str(i) + ".com" for i in range(100000)]
domains_sorted = sorted(domains)
with open('test.txt', 'w') as f:
    pass
"""

t1 = timeit.timeit("with open('test.txt', 'w') as f:\n for d in domains_sorted:\n  f.write(f'{d}\\n')", setup=setup, number=10)
t2 = timeit.timeit("with open('test.txt', 'w') as f:\n f.write('\\n'.join(domains_sorted) + '\\n')", setup=setup, number=10)

print(f"write loop: {t1}")
print(f"write join: {t2}")
