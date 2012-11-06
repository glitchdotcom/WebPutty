import datetime
import time
import logging
import os
import cPickle as pickle
import re

# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

import StringIO
from types import GeneratorType
import zlib

from google.appengine.ext.webapp import template, RequestHandler
from google.appengine.api import memcache

import unformatter
from pprint import pformat
import cleanup
import cookies

import gae_mini_profiler.config
if os.environ["SERVER_SOFTWARE"].startswith("Devel"):
    config = gae_mini_profiler.config.ProfilerConfigDevelopment
else:
    config = gae_mini_profiler.config.ProfilerConfigProduction

# request_id is a per-request identifier accessed by a couple other pieces of gae_mini_profiler
request_id = None

class SharedStatsHandler(RequestHandler):

    def get(self):
        path = os.path.join(os.path.dirname(__file__), "templates/shared.html")

        request_id = self.request.get("request_id")
        if not RequestStats.get(request_id):
            self.response.out.write("Profiler stats no longer exist for this request.")
            return

        self.response.out.write(
            template.render(path, {
                "request_id": request_id
            })
        )

class RequestStatsHandler(RequestHandler):

    def get(self):

        self.response.headers["Content-Type"] = "application/json"

        list_request_ids = []

        request_ids = self.request.get("request_ids")
        if request_ids:
            list_request_ids = request_ids.split(",")

        list_request_stats = []

        for request_id in list_request_ids:

            request_stats = RequestStats.get(request_id)

            if request_stats and not request_stats.disabled:

                dict_request_stats = {}
                for property in RequestStats.serialized_properties:
                    dict_request_stats[property] = request_stats.__getattribute__(property)

                list_request_stats.append(dict_request_stats)

                # Don't show temporary redirect profiles more than once automatically, as they are
                # tied to URL params and may be copied around easily.
                if request_stats.temporary_redirect:
                    request_stats.disabled = True
                    request_stats.store()

        self.response.out.write(json.dumps(list_request_stats))

class RequestStats(object):

    serialized_properties = ["request_id", "url", "url_short", "s_dt",
                             "profiler_results", "appstats_results", "simple_timing",
                             "temporary_redirect", "logs"]

    def __init__(self, request_id, environ, middleware):
        self.request_id = request_id

        self.url = environ.get("PATH_INFO")
        if environ.get("QUERY_STRING"):
            self.url += "?%s" % environ.get("QUERY_STRING")

        self.url_short = self.url
        if len(self.url_short) > 26:
            self.url_short = self.url_short[:26] + "..."

        self.simple_timing = middleware.simple_timing
        self.s_dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.profiler_results = RequestStats.calc_profiler_results(middleware)
        self.appstats_results = RequestStats.calc_appstats_results(middleware)
        self.logs = middleware.logs

        self.temporary_redirect = middleware.temporary_redirect
        self.disabled = False

    def store(self):
        # Store compressed results so we stay under the memcache 1MB limit
        pickled = pickle.dumps(self)
        compressed_pickled = zlib.compress(pickled)

        return memcache.set(RequestStats.memcache_key(self.request_id), compressed_pickled)

    @staticmethod
    def get(request_id):
        if request_id:

            compressed_pickled = memcache.get(RequestStats.memcache_key(request_id))

            if compressed_pickled:
                pickled = zlib.decompress(compressed_pickled)
                return pickle.loads(pickled)

        return None

    @staticmethod
    def memcache_key(request_id):
        if not request_id:
            return None
        return "__gae_mini_profiler_request_%s" % request_id

    @staticmethod
    def seconds_fmt(f):
        return RequestStats.milliseconds_fmt(f * 1000)

    @staticmethod
    def milliseconds_fmt(f):
        return ("%.5f" % f).rstrip("0").rstrip(".")

    @staticmethod
    def short_method_fmt(s):
        return s[s.rfind("/") + 1:]

    @staticmethod
    def short_rpc_file_fmt(s):
        if not s:
            return ""
        return s[s.find("/"):]

    @staticmethod
    def calc_profiler_results(middleware):

        if middleware.simple_timing:
            return {
                "total_time": RequestStats.seconds_fmt(middleware.end - middleware.start),
            }

        import pstats

        # Make sure nothing is printed to stdout
        output = StringIO.StringIO()
        stats = pstats.Stats(middleware.prof, stream=output)
        stats.sort_stats("cumulative")

        results = {
            "total_call_count": stats.total_calls,
            "total_time": RequestStats.seconds_fmt(stats.total_tt),
            "calls": []
        }

        width, list_func_names = stats.get_print_list([80])
        for func_name in list_func_names:
            primitive_call_count, total_call_count, total_time, cumulative_time, callers = stats.stats[func_name]

            func_desc = pstats.func_std_string(func_name)

            callers_names = map(lambda func_name: pstats.func_std_string(func_name), callers.keys())
            callers_desc = map(
                    lambda name: {"func_desc": name, "func_desc_short": RequestStats.short_method_fmt(name)},
                    callers_names)

            results["calls"].append({
                "primitive_call_count": primitive_call_count,
                "total_call_count": total_call_count,
                "total_time": RequestStats.seconds_fmt(total_time),
                "per_call": RequestStats.seconds_fmt(total_time / total_call_count) if total_call_count else "",
                "cumulative_time": RequestStats.seconds_fmt(cumulative_time),
                "per_call_cumulative": RequestStats.seconds_fmt(cumulative_time / primitive_call_count) if primitive_call_count else "",
                "func_desc": func_desc,
                "func_desc_short": RequestStats.short_method_fmt(func_desc),
                "callers_desc": callers_desc,
            })

        output.close()

        return results

    @staticmethod
    def calc_appstats_results(middleware):
        if middleware.recorder:

            total_call_count = 0
            total_time = 0
            calls = []
            service_totals_dict = {}
            likely_dupes = False
            end_offset_last = 0

            requests_set = set()

            appstats_key = long(middleware.recorder.start_timestamp * 1000)

            for trace in middleware.recorder.traces:
                total_call_count += 1

                total_time += trace.duration_milliseconds()

                # Don't accumulate total RPC time for traces that overlap asynchronously
                if trace.start_offset_milliseconds() < end_offset_last:
                    total_time -= (end_offset_last - trace.start_offset_milliseconds())
                end_offset_last = trace.start_offset_milliseconds() + trace.duration_milliseconds()

                service_prefix = trace.service_call_name()

                if "." in service_prefix:
                    service_prefix = service_prefix[:service_prefix.find(".")]

                if service_prefix not in service_totals_dict:
                    service_totals_dict[service_prefix] = {
                        "total_call_count": 0,
                        "total_time": 0,
                        "total_misses": 0,
                    }

                service_totals_dict[service_prefix]["total_call_count"] += 1
                service_totals_dict[service_prefix]["total_time"] += trace.duration_milliseconds()

                stack_frames_desc = []
                for frame in trace.call_stack_list():
                    stack_frames_desc.append("%s:%s %s" %
                            (RequestStats.short_rpc_file_fmt(frame.class_or_file_name()),
                                frame.line_number(),
                                frame.function_name()))

                request = trace.request_data_summary()
                response = trace.response_data_summary()

                likely_dupe = request in requests_set
                likely_dupes = likely_dupes or likely_dupe
                requests_set.add(request)

                request_short = request_pretty = None
                response_short = response_pretty = None
                miss = 0
                try:
                    request_object = unformatter.unformat(request)
                    response_object = unformatter.unformat(response)

                    request_short, response_short, miss = cleanup.cleanup(request_object, response_object)

                    request_pretty = pformat(request_object)
                    response_pretty = pformat(response_object)
                except Exception, e:
                    logging.warning("Prettifying RPC calls failed.\n%s", e)

                service_totals_dict[service_prefix]["total_misses"] += miss

                calls.append({
                    "service": trace.service_call_name(),
                    "start_offset": RequestStats.milliseconds_fmt(trace.start_offset_milliseconds()),
                    "total_time": RequestStats.milliseconds_fmt(trace.duration_milliseconds()),
                    "request": request_pretty or request,
                    "response": response_pretty or response,
                    "request_short": request_short or cleanup.truncate(request),
                    "response_short": response_short or cleanup.truncate(response),
                    "stack_frames_desc": stack_frames_desc,
                    "likely_dupe": likely_dupe,
                })

            service_totals = []
            for service_prefix in service_totals_dict:
                service_totals.append({
                    "service_prefix": service_prefix,
                    "total_call_count": service_totals_dict[service_prefix]["total_call_count"],
                    "total_misses": service_totals_dict[service_prefix]["total_misses"],
                    "total_time": RequestStats.milliseconds_fmt(service_totals_dict[service_prefix]["total_time"]),
                })
            service_totals = sorted(service_totals, reverse=True, key=lambda service_total: float(service_total["total_time"]))

            return  {
                        "appstats_available": True,
                        "total_call_count": total_call_count,
                        "total_time": RequestStats.milliseconds_fmt(total_time),
                        "calls": calls,
                        "service_totals": service_totals,
                        "likely_dupes": likely_dupes,
                        "appstats_key": appstats_key,
                    }

        return { "appstats_available": False, }

class ProfilerWSGIMiddleware(object):

    def __init__(self, app):
        template.register_template_library('gae_mini_profiler.templatetags')
        self.app = app
        self.app_clean = app
        self.prof = None
        self.recorder = None
        self.temporary_redirect = False
        self.handler = None
        self.logs = None
        self.simple_timing = False
        self.start = None
        self.end = None

    def __call__(self, environ, start_response):

        global request_id
        request_id = None

        # Start w/ a non-profiled app at the beginning of each request
        self.app = self.app_clean
        self.prof = None
        self.recorder = None
        self.temporary_redirect = False
        self.simple_timing = cookies.get_cookie_value("g-m-p-disabled") == "1"

        # Never profile calls to the profiler itself to avoid endless recursion.
        if config.should_profile(environ) and not environ.get("PATH_INFO", "").startswith("/gae_mini_profiler/"):

            # Set a random ID for this request so we can look up stats later
            import base64
            request_id = base64.urlsafe_b64encode(os.urandom(5))

            # Send request id in headers so jQuery ajax calls can pick
            # up profiles.
            def profiled_start_response(status, headers, exc_info = None):

                if status.startswith("302 "):
                    # Temporary redirect. Add request identifier to redirect location
                    # so next rendered page can show this request's profile.
                    headers = ProfilerWSGIMiddleware.headers_with_modified_redirect(environ, headers)
                    self.temporary_redirect = True

                # Append headers used when displaying profiler results from ajax requests
                headers.append(("X-MiniProfiler-Id", request_id))
                headers.append(("X-MiniProfiler-QS", environ.get("QUERY_STRING")))

                return start_response(status, headers, exc_info)

            if self.simple_timing:

                # Detailed recording is disabled. Just track simple start/stop time.
                self.start = time.clock()

                result = self.app(environ, profiled_start_response)
                for value in result:
                    yield value

                self.end = time.clock()

            else:

                # Add logging handler
                self.add_handler()

                # Monkey patch appstats.formatting to fix string quoting bug
                # See http://code.google.com/p/googleappengine/issues/detail?id=5976
                import unformatter.formatting
                import google.appengine.ext.appstats.formatting
                google.appengine.ext.appstats.formatting._format_value = unformatter.formatting._format_value

                # Configure AppStats output, keeping a high level of request
                # content so we can detect dupe RPCs more accurately
                from google.appengine.ext.appstats import recording
                recording.config.MAX_REPR = 750

                # Turn on AppStats monitoring for this request
                old_app = self.app
                def wrapped_appstats_app(environ, start_response):
                    # Use this wrapper to grab the app stats recorder for RequestStats.save()

                    if recording.recorder_proxy.has_recorder_for_current_request():
                        self.recorder = recording.recorder_proxy.get_for_current_request()

                    return old_app(environ, start_response)
                self.app = recording.appstats_wsgi_middleware(wrapped_appstats_app)

                # Turn on cProfile profiling for this request
                import cProfile
                self.prof = cProfile.Profile()

                # Get profiled wsgi result
                result = self.prof.runcall(lambda *args, **kwargs: self.app(environ, profiled_start_response), None, None)

                # If we're dealing w/ a generator, profile all of the .next calls as well
                if type(result) == GeneratorType:

                    while True:
                        try:
                            yield self.prof.runcall(result.next)
                        except StopIteration:
                            break

                else:
                    for value in result:
                        yield value

                self.logs = self.get_logs(self.handler)
                logging.getLogger().removeHandler(self.handler)
                self.handler.stream.close()
                self.handler = None

            # Store stats for later access
            RequestStats(request_id, environ, self).store()

            # Just in case we're using up memory in the recorder and profiler
            self.recorder = None
            self.prof = None
            request_id = None

        else:
            result = self.app(environ, start_response)
            for value in result:
                yield value

    def add_handler(self):
        if self.handler is None:
            self.handler = ProfilerWSGIMiddleware.create_handler()
        logging.getLogger().addHandler(self.handler)

    @staticmethod
    def create_handler():
        handler = logging.StreamHandler(StringIO.StringIO())
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("\t".join([
            '%(levelno)s',
            '%(asctime)s%(msecs)d',
            '%(funcName)s',
            '%(filename)s',
            '%(lineno)d',
            '%(message)s',
        ]), '%M:%S.')
        handler.setFormatter(formatter)
        return handler

    @staticmethod
    def get_logs(handler):
        raw_lines = [l for l in handler.stream.getvalue().split("\n") if l]

        lines = []
        for line in raw_lines:
            if "\t" in line:
                fields = line.split("\t")
                lines.append(fields)
            else: # line is part of a multiline log message (prob a traceback)
                prevline = lines[-1][-1]
                if prevline: # ignore leading blank lines in the message
                    prevline += "\n"
                prevline += line
                lines[-1][-1] = prevline

        return lines

    @staticmethod
    def headers_with_modified_redirect(environ, headers):
        headers_modified = []

        for header in headers:
            if header[0] == "Location":
                reg = re.compile("mp-r-id=([^&]+)")

                # Keep any chain of redirects around
                request_id_chain = request_id
                match = reg.search(environ.get("QUERY_STRING"))
                if match:
                    request_id_chain = ",".join([match.groups()[0], request_id])

                # Remove any pre-existing miniprofiler redirect id
                location = header[1]
                location = reg.sub("", location)
                location_hash = False
                if "#" in location:
                  location, location_hash = location.split("#", 1)

                # Add current request id as miniprofiler redirect id
                location += ("&" if "?" in location else "?")
                location = location.replace("&&", "&")
                location += "mp-r-id=%s" % request_id_chain
                if location_hash:
                  location += "#%s" % location_hash

                headers_modified.append((header[0], location))
            else:
                headers_modified.append(header)

        return headers_modified
