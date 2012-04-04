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

from utils import adjust_sys_path
adjust_sys_path()

from datetime import datetime
import logging
import os
import simplejson
import wsgiref.handlers

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from livecount import counter
from livecount.counter import LivecountCounter
from livecount.counter import PeriodType


class CounterHandler(webapp.RequestHandler):
    """
    Handles displaying the values of the counters
    and requests to increment/decrement counters.
    """

    def get(self):
        namespace = self.request.get('namespace')
        period_type = self.request.get('period_type')
        period_types = self.request.get('period_types').replace(" ", "")
        period = self.request.get('period')
        name = self.request.get('counter_name')
        delta = self.request.get('delta')
        fetch_limit = self.request.get('fetch_limit')
    
        if not namespace:
            namespace = "default"
        if not period_type:
            period_type = PeriodType.DAY
        if not period_types:
            period_types = PeriodType.DAY + "," + PeriodType.WEEK
        if not period:
            period = str(datetime.now()).split(".")[0]
        if not delta:
            delta = 1
        if not fetch_limit:
            fetch_limit = "20"
        
        modified_counter = None
        if name:
            full_key = LivecountCounter.KeyName(namespace, period_type, period, name)
            modified_counter = LivecountCounter.get_by_key_name(full_key)
            
        counter_entities_query = LivecountCounter.all().order('-count')
        if namespace:
            counter_entities_query.filter("namespace = ", namespace)
        if period_type:
            counter_entities_query.filter("period_type = ", period_type)
        scoped_period = PeriodType.find_scope(period_type, period)
        if period:
            counter_entities_query.filter("period = ", scoped_period)
        counter_entities = counter_entities_query.fetch(int(fetch_limit))
        logging.info("counter_entities: " + str(counter_entities))
    
        stats = counter.GetMemcacheStats()
        
        template_values = {
                           'namespace': namespace,
                           'period_type': period_type,
                           'period_types': period_types,
                           'period': period,
                           'counter_name': name,
                           'delta': delta,
                           'modified_counter': modified_counter,
                           'counters': counter_entities,
                           'stats': stats
                           }
        logging.info("template_values: " + str(template_values))
        template_file = os.path.join(os.path.dirname(__file__), 'counter_admin.html')
        self.response.out.write(template.render(template_file, template_values))


    def post(self):
        namespace = self.request.get('namespace')
        period_type = self.request.get('period_type')
        period_types = self.request.get('period_types').replace(" ", "")
        period = self.request.get('period')
        name = self.request.get('counter_name')
        delta = self.request.get('delta')
        type = self.request.get('type')
        
        if type == "Increment Counter":
            counter.load_and_increment_counter(name=name, period=period, period_types=period_types.split(","), namespace=namespace, delta=long(delta))
        elif type == "Decrement Counter":
            counter.load_and_decrement_counter(name=name, period=period, period_types=period_types.split(","), namespace=namespace, delta=long(delta))
    
        logging.info("Redirecting to: /livecount/counter_admin?namespace=" + namespace + "&period_type=" + period_type + "&period_types=" + period_types + "&period=" + period + "&counter_name=" + name + "&delta=" + delta)
        self.redirect("/livecount/counter_admin?namespace=" + namespace + "&period_type=" + period_type + "&period_types=" + period_types + "&period=" + period + "&counter_name=" + name + "&delta=" + delta)


def main():
    application = webapp.WSGIApplication(
    [  
        ('/livecount/counter_admin', CounterHandler),
    ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
