import sys
import os

def adjust_sys_path(dir_name='libs'):
    """
    Patch to search the libs folder. At the moment, I believe it's unable to
    find .egg's, but it does search libs for imports before anything else.
    """
    root_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(root_dir, dir_name))


def find_gae_sdk(dir_name='libs'):
    """
    Correct any ImportError caused from being unable to find Google App
    Engine's SDK. These normally occur when trying to run the application
    from the commandline and/or when testing.
    """
    adjust_sys_path(dir_name)
    from gae_path.util import gae_sdk_path, add_gae_sdk_path
    add_gae_sdk_path()
    path = gae_sdk_path()
    sys.path.extend([path + "/lib/yaml/lib",
                     path + "/lib/fancy_urllib",
                     path + "/lib/webob"])

