import inspect
import sys
# try to see what submit requires
try:
    # Just need to check the function signature since the tool call failed
    import tools.submit
    print(inspect.signature(tools.submit.submit))
except Exception as e:
    print(e)
