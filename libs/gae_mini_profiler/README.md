# Google App Engine Mini Profiler

gae_mini_profiler is a quick drop-in WSGI app that provides ubiquitous profiling of your existing GAE projects. It exposes both RPC statistics and standard profiling output for users of your choosing on your production site. Only requests coming from users of your choosing will be profiled, and others will not suffer any performance degradation. See screenshots and features below.

This project is heavily inspired by the impressive [mvc-mini-profiler](http://code.google.com/p/mvc-mini-profiler/).

gae_mini_profiler is [MIT licensed](http://en.wikipedia.org/wiki/MIT_License).

* <a href="#demo">Demo</a>  
* <a href="#screens">Screenshots</a>  
* <a href="#start">Getting Started</a>  
* <a href="#features">Features</a>  
* <a href="#bonus">Bonus</a>  

## <a name="demo">Demo</a>

You can play around with one of GAE's sample applications with gae_mini_profiler enabled for all users via [http://gae-mini-profiler.appspot.com](http://gae-mini-profiler.appspot.com/).

## <a name="screens">Screenshots</a>

<img src="http://gae-mini-profiler.appspot.com/images/gae-mini-profiler/corner.png"/><br/><em>All profiled pages have total milliseconds in corner, which can be expanded...</em><br/><br/>
<img src="http://gae-mini-profiler.appspot.com/images/gae-mini-profiler/expanded.png"/><br/><em>...to show more details...</em><br/><br/>
<img src="http://gae-mini-profiler.appspot.com/images/gae-mini-profiler/rpc.png"/><br/><em>...about remote procedure call performance...</em><br/><br/>
<img src="http://gae-mini-profiler.appspot.com/images/gae-mini-profiler/profile.png"/><br/><em>...or standard profiler output.</em><br/><br/>
<img src="http://gae-mini-profiler.appspot.com/images/gae-mini-profiler/ajax-corner.png?test"/><br/><em>Ajax requests are also profiled and details made available as they are received.</em>

## <a name="start">Getting Started</a>

1. Download this repository's source and copy the `gae_mini_profiler/` folder into your App Engine project's root directory.
2. Add the following two handler definitions to `app.yaml`:
<pre>
handlers:
&ndash; url: /gae_mini_profiler/static
&nbsp;&nbsp;static_dir: gae_mini_profiler/static<br/>
&ndash; url: /gae_mini_profiler/.*
&nbsp;&nbsp;script: gae_mini_profiler/main.py
</pre>
3. Modify the WSGI application you want to profile by wrapping it with the gae_mini_profiler WSGI application:
<pre>
&#35; Example of existing application
application = webapp.WSGIApplication(...existing application...)<br/>
&#35; Add the following
from gae_mini_profiler import profiler
application = profiler.ProfilerWSGIMiddleware(application)
</pre>
4. Insert the `profiler_includes` template tag below jQuery somewhere (preferably at the end of your template):
<pre>
        ...your html...
        {% profiler_includes %}
    &lt;/body&gt;
&lt;/html&gt;
</pre>
5. You're all set! Just choose the users for whom you'd like to enable profiling in `gae_mini_profiler/config.py`:
<pre>
&#35; If using the default should_profile implementation, the profiler
&#35; will only be enabled for requests made by the following GAE users.
enabled_profiler_emails = [
    "kamens@gmail.com",
]
</pre>

## <a name="features">Features</a>

* Production profiling without impacting normal users
* Easily profile all requests, including ajax calls
* Summaries of RPC call types and their performance so you can quickly figure out whether datastore, memcache, or urlfetch is your bottleneck
* Share individual profile results with others by sending link
* Duplicate RPC calls are flagged for easy spotting in case you're repeating memcache or datastore queries.
* Quickly sort and examine profiler stats and call stacks

## <a name="bonus">Bonus</a>

gae_mini_profiler is currently in production use at Khan Academy (http://khanacademy.org). If you make find good use of it elsewhere, be sure to let me know.