from google.appengine.api import users

# If using the default should_profile implementation, the profiler
# will only be enabled for requests made by the following GAE users.
enabled_profiler_emails = [
    "test@example.com",
    "test1@example.com",
]

# Customize should_profile to return true whenever a request should be profiled.
# This function will be run once per request, so make sure its contents are fast.
class ProfilerConfigProduction:
    @staticmethod
    def should_profile(environ):
        user = users.get_current_user()
        return user and user.email() in enabled_profiler_emails

class ProfilerConfigDevelopment:
    @staticmethod
    def should_profile(environ):
        return users.is_current_user_admin()
