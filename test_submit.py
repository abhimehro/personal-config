import sys
import inspect
from types import ModuleType

# This is a hack to try to discover how `submit` might be registered
# Since it failed because of missing title and description
