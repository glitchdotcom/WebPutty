# Google App Engine Mini Profiler

gae_mini_profiler is a quick drop-in WSGI app that provides ubiquitous profiling of your existing GAE projects. It exposes both RPC statistics and standard profiling output for users of your choosing on your production site. Only requests coming from users of your choosing will be profiled, and others will not suffer any performance degradation. See screenshots and features below.

This project is heavily inspired by the impressive [mvc-mini-profiler](http://code.google.com/p/mvc-mini-profiler/).

gae_mini_profiler is [MIT licensed](http://en.wikipedia.org/wiki/MIT_License).

* <a href="#demo">Demo</a>
* <a href="#screens">Screenshots</a>
* <a href="#start">Getting Started</a>
* <a href="#features">Features</a>
* <a href="#dependencies">Dependencies</a>
* <a href="#bonus">Bonus</a>
* <a href="#faq">FAQ</a>

## <a name="demo">Demo</a>

You can play around with one of GAE's sample applications with gae_mini_profiler enabled for all users via [http://gae-mini-profiler.appspot.com](http://gae-mini-profiler.appspot.com/).

## <a name="screens">Screenshots</a>

<img src="http://gae-mini-profiler.appspot.com/images/gae-mini-profiler/corner.png"/><br/><em>All profiled pages have total milliseconds in corner, which can be expanded...</em><br/><br/>
<img src="http://gae-mini-profiler.appspot.com/images/gae-mini-profiler/expanded.png"/><br/><em>...to show more details...</em><br/><br/>
<img src="http://gae-mini-profiler.appspot.com/images/gae-mini-profiler/rpc.png"/><br/><em>...about remote procedure call performance...</em><br/><br/>
<img src="http://gae-mini-profiler.appspot.com/images/gae-mini-profiler/profile.png"/><br/><em>...or standard profiler output.</em><br/><br/>
<img src="http://gae-mini-profiler.appspot.com/images/gae-mini-profiler/ajax-corner.png?test"/><br/><em>Ajax requests are also profiled and details made available as they are received.</em><br/><br/>
<img src="http://i.imgur.com/SG0dp.png"/><br/><em>Any Python logging module output is also available for easy access.</em>

## <a name="start">Getting Started</a>

1. Download this repository's source and copy the `gae_mini_profiler/` folder into your App Engine project's root directory.

2. Add the following two handler definitions to `app.yaml`:

        handlers:
        - url: /gae_mini_profiler/static
          static_dir: gae_mini_profiler/static
        - url: /gae_mini_profiler/.*
          script: gae_mini_profiler/main.py

3. Modify the WSGI application you want to profile by wrapping it with the gae_mini_profiler WSGI application. This is usually done in `appengine_config.py`:

        import gae_mini_profiler.profiler
        gae_mini_profiler_ENABLED_PROFILER_EMAILS = ['m.dornseif@hudora.de']

        def webapp_add_wsgi_middleware(app):
            """Called with each WSGI handler initialisation"""
            app = gae_mini_profiler.profiler.ProfilerWSGIMiddleware(app)
            return app

4. If you use Django Templates insert the `profiler_includes` template tag below jQuery somewhere (preferably at the end of your template):

                ...your html...
                {% profiler_includes %}
            </body>
        </html>

    Alternatively on any other template system you can hardcode the call.
    
    For example in jinja2 first add a function to template globals that can retrieve the request_id, something like:
    
        from gae_mini_profiler import profiler
        def get_request_id():
            return profiler.request_id
        jinja_env.globals['get_request_id'] = get_request_id

    Than add this to your template:

        <link rel="stylesheet" type="text/css" href="/gae_mini_profiler/static/css/profiler.css" />
        <script type="text/javascript" src="/gae_mini_profiler/static/js/profiler.js"></script>
        <script type="text/javascript">GaeMiniProfiler.init("{{get_request_id()}}", false)</script>

    If you use the static inclusion you probably should use your template engine to include the code only
for admins or other profiling-prone users.

5. You're all set! Just choose the users for whom you'd like to enable profiling by putting the respective E-Mail addresses in `gae_mini_profiler/config.py`:

            enabled_profiler_emails = ['user1@example.com',
                                       'user2@example.com']

For more sophisticated choice of what to profile check `gae_mini_profiler/config.py`.


## <a name="features">Features</a>

* Production profiling without impacting normal users
* Easily profile all requests, including ajax calls
* Summaries of RPC call types and their performance so you can quickly figure out whether datastore, memcache, or urlfetch is your bottleneck
* Redirect chains are tracked -- quickly examine the profile of not just the currently rendered request, but any preceding request that issued a 302 redirect leading to the current page.
* Share individual profile results with others by sending link
* Duplicate RPC calls are flagged for easy spotting in case you're repeating memcache or datastore queries.
* Quickly sort and examine profiler stats and call stacks

## <a name="dependencies">Dependencies</a>

* jQuery must be included somewhere on your page.
* (Optional) If you want the fancy slider selector for the Logs output, jQuery UI must also be included with its Slider plugin.

## <a name="bonus">Bonus</a>

gae_mini_profiler is currently in production use at [Khan Academy](http://khanacademy.org) as well as [WebPutty](http://www.webputty.net). If you make good use of it elsewhere, be sure to let me know.

## <a name="faq">FAQ</a>

1. I had my appstats_RECORD_FRACTION variable set to 0.1, which means only 10% of my queries were getting profiles generated.  This meant that most of the time gae_mini_profiler was failing with a javascript error, because the appstats variable was null.

    If you are using appengine_config.py to customize Appstats behavior you should add this to the top of your "appstats_should_record" method.
<pre>def appstats_should_record(env):
        from gae_mini_profiler.config import should_profile
        if should_profile(env):
            return True
</pre>
