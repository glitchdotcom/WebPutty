#
# Copyright 2011 Greg Bayer <greg@gbayer.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from datetime import datetime, timedelta
import logging
import time
import wsgiref.handlers

from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from google.appengine.ext import webapp


""" 
  Livecount is a memcache-based counter api with asynchronous writes to persist counts to datastore.
  
  Semantics:
   - Write-Behind
   - Read-Through
"""

class PeriodType(object):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    ALL = "all"

    @staticmethod
    def find_scope(period_type, period):
        if period_type == PeriodType.SECOND:
            return str(period)[0:19] # 2011-06-13 18:11:32
        elif period_type == PeriodType.MINUTE:
            return str(period)[0:16] # 2011-06-13 18:11
        elif period_type == PeriodType.HOUR:
            return str(period)[0:13] # 2011-06-13 18
        elif period_type == PeriodType.DAY:
            return str(period)[0:10] # 2011-06-13
        elif period_type == PeriodType.WEEK:
            if not isinstance(period, datetime):
                period = PeriodType.str_to_datetime(period)
            return str(period- timedelta(period.weekday()))[0:10]+"week" # 2011-06-13week; use Monday as marker
        elif period_type == PeriodType.MONTH:
            return str(period)[0:7] # 2011-06
        elif period_type == PeriodType.YEAR:
            return str(period)[0:4] # 2011
        else:
            return "all"

    @staticmethod
    def str_to_datetime(datetime_str):
        time_format = "%Y-%m-%d %H:%M:%S"
        return datetime.fromtimestamp(time.mktime(time.strptime(datetime_str.split('.')[0], time_format)))


class LivecountCounter(db.Model):
    namespace = db.StringProperty(default="default")
    period_type = db.StringProperty(default=PeriodType.ALL)
    period = db.StringProperty()
    name = db.StringProperty()
    count = db.IntegerProperty()
    
    @staticmethod
    def KeyName(namespace, period_type, period, name):
        scoped_period = PeriodType.find_scope(period_type, period)
        return namespace + ":" + period_type + ":" + scoped_period + ":" + name
    
    @staticmethod
    def PartialKeyName(period_type, period, name):
        scoped_period = PeriodType.find_scope(period_type, period)
        return period_type + ":" + scoped_period + ":" + name


def load_and_get_count(name, namespace='default', period_type='all', period=datetime.now()):
    # Try memcache first
    partial_key = LivecountCounter.PartialKeyName(period_type, period, name)
    count =  memcache.get(partial_key, namespace=namespace) 
    
    # Not in memcache
    if count is None:
        # See if this counter already exists in the datastore
        full_key = LivecountCounter.KeyName(namespace, period_type, period, name)
        record = LivecountCounter.get_by_key_name(full_key)
        # If counter exists in the datastore, but is not currently in memcache, add it
        if record:
            count = record.count
            memcache.add(partial_key, count, namespace=namespace)
    
    return count


def load_and_increment_counter(name, period=datetime.now(), period_types=[PeriodType.ALL], namespace='default', delta=1, batch_size=None):
    """
    Setting batch size allows control of how often a writeback worker is created.
    By default, this happens at every increment to ensure maximum durability.
    If there is already a worker waiting to write the value of a counter, another will not be created.
    """    
    # Warning: There is a race condition here. If two processes try to load
    # the same value from the datastore, one's update may be lost.
    # TODO: Think more about whether we care about this...
    
    for period_type in period_types:
        current_count = None
        
        result = None
        partial_key = LivecountCounter.PartialKeyName(period_type, period, name)
        if delta >= 0:
            result = memcache.incr(partial_key, delta, namespace=namespace)
        else: # Since increment by negative number is not supported, convert to decrement
            result = memcache.decr(partial_key, -delta, namespace=namespace)
        
        if result is None:
            # See if this counter already exists in the datastore
            full_key = LivecountCounter.KeyName(namespace, period_type, period, name)
            record = LivecountCounter.get_by_key_name(full_key)
            if record:
                # Load last value from datastore
                new_counter_value = record.count + delta
                if new_counter_value < 0: new_counter_value = 0  # To match behavior of memcache.decr(), don't allow negative values
                memcache.add(partial_key, new_counter_value, namespace=namespace)
                if batch_size: current_count = record.count
            else:
                # Start new counter
                memcache.add(partial_key, delta, namespace=namespace)
                if batch_size: current_count = delta
        else:
            if batch_size: current_count = memcache.get(partial_key, namespace=namespace)
            
        # If batch_size is set, only try creating one worker per batch
        if not batch_size or (batch_size and current_count % batch_size == 0):
            if memcache.add(partial_key + '_dirty', delta, namespace=namespace):
                #logging.info("Adding task to taskqueue. counter value = " + str(memcache.get(partial_key, namespace=namespace)))
                taskqueue.add(queue_name='livecount-writebacks', url='/livecount/worker', params={'name': name, 'period': period, 'period_type': period_type, 'namespace': namespace}) # post parameter


def load_and_decrement_counter(name, period=datetime.now(), period_types=[PeriodType.ALL], namespace='default', delta=1, batch_size=None):
    load_and_increment_counter(name, period, period_types, namespace, -delta, batch_size)

    
def GetMemcacheStats():
    stats = memcache.get_stats()
    return stats


class LivecountCounterWorker(webapp.RequestHandler):
    def post(self):
        namespace = self.request.get('namespace')
        period_type = self.request.get('period_type')
        period = self.request.get('period')
        name = self.request.get('name')
        
        full_key = LivecountCounter.KeyName(namespace, period_type, period, name)
        partial_key = LivecountCounter.PartialKeyName(period_type, period, name)
       
        memcache.delete(partial_key + '_dirty', namespace=namespace)
        cached_count = memcache.get(partial_key, namespace=namespace)
        if cached_count is None:
            logging.error('LivecountCounterWorker: Failure for partial key=%s', partial_key)
            return
        
        # add new row in datastore
        scoped_period = PeriodType.find_scope(period_type, period)
        LivecountCounter(key_name=full_key, namespace=namespace, period_type=period_type, period=scoped_period, name=name, count=cached_count).put()


class WritebackAllCountersHandler(webapp.RequestHandler):
    """
    Writes back all counters from memory to the datastore
    """
    def get(self):
        namespace = self.request.get('namespace')
        delete = self.request.get('delete')
        
        logging.info("Writing back all counters from memory to the datastore. Namespace=%s. Delete from memory=%s." % (str(namespace), str(delete)))
        result = False
        while not result:
            result=in_memory_counter.WritebackAllCounters(namespace, delete)
        
        self.response.out.write("Done. WritebackAllCounters succeeded = " + str(result))


class ClearEntireCacheHandler(webapp.RequestHandler):
    """
    Clears entire memcache
    """
    def get(self):
        logging.info("Deleting all counters in memcache. Any counts not previously flushed will be lost.")
        
        result = in_memory_counter.ClearEntireCache()
        self.response.out.write("Done. ClearEntireCache succeeded = " + str(result))


class RedirectToCounterAdminHandler(webapp.RequestHandler):
    """ For convenience / demo purposes, redirect to counter admin page.
    """
    def get(self):
        self.redirect('/livecount/counter_admin')


def main():
    logging.getLogger().setLevel(logging.DEBUG)
    application = webapp.WSGIApplication([
         ('/livecount/worker', LivecountCounterWorker),
         ('/livecount/writeback_all_counters', WritebackAllCountersHandler),
         ('/livecount/clear_entire_cache', ClearEntireCacheHandler),
         ('/', RedirectToCounterAdminHandler)
    ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
