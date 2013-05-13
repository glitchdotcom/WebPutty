# WebPutty: The Open Source Transmogrifier

<img src="http://blog.fogcreek.com/wp-content/uploads/2011/07/transmogrifier_small.png" width="300" height="300" alt="WebPutty Transmogrifier" title="WebPutty Transmogrifier" style="float: right;" />

## What the what?

WebPutty is a simple CSS editing and hosting service that you can run on [Google App Engine](https://developers.google.com/appengine/).

WebPutty gives you a syntax-highlighting CSS editor you can use from anywhere, the power of [SCSS](http://sass-lang.com/) and [Compass](http://compass-style.org/), a side-by-side preview pane, and instant publishing with minification, compression, and automatic cache control.

You can get started with just a pair of tags in your website's template and WebPutty will host and serve your published CSS minified and gzipped for super speed.

Intrigued? Read more about [the motivation behind WebPutty](http://blog.fogcreek.com/webputty-css-editing-goes-boink/?fccmp=webputty), [how it came to be](http://tghw.com/blog/lean-development-zero-to-launch-in-six-weeks/), and [how it ended up being open-source](http://blog.fogcreek.com/whats-up-with-webputty/?fccmp=webputty).

## How to get WebPutty up and running on your very own sparkly Google App Engine account:

1. Download and install [Python 2.7](http://www.python.org/getit/releases/2.7.4/) and the [Google App Engine SDK for Python](https://developers.google.com/appengine/downloads)
- Clone this repo
- [Log into Google App Engine](https://appengine.google.com/) and create a new application
- Open up app.yaml in the root of this repo and update `application` to match the name of your newly created Google App Engine application
- Open up settings.py (also in the root of this repo) and update the following variables:
	* `invite_sender_email`
	* `incoming_sender_email`
	* `forward_mail_to`
	* `secret_key`

- Install [pip](http://pypi.python.org/pypi/pip)
- `pip install fabric`
- `fab deploy`
- `sip lemonade`

# Advanced Setup:
### For page preview images:
- Go to http://url2png.com and sign up for an account
	- Add these settings to the `url2png` section in settings.py

### To store WebPutty stylesheets using Google Cloud Storage (faster and cheaper than GAE):
- Sign up for [Google Cloud Storage](https://developers.google.com/storage/) via [Google's API console](https://code.google.com/apis/console/)
	- Update `google_bucket` and `use_google_cloud_storage` in settings.py

# Copyright

Copyright (c) 2011-2013 Fog Creek Software Inc.

Some of the icons, images, and sample HTML &amp; CSS used by WebPutty are licensed under the following terms:

- [Creative Commons Attribution License](http://creativecommons.org/licenses/by/3.0/)
  * FatCow Web Hosting, [Farm-Fresh Web Icon Pack](http://www.fatcow.com/free-icons)
  * design deck, [IC Minimal Icon Set](http://www.designdeck.co.uk/article_details.php?id=246)
  * Yusuke Kamiyamane, [Fugue Icon Pack](http://p.yusukekamiyamane.com/)
  * Mark Pilgrim, [Dive into HTML5](http://diveintohtml5.org)

- [Creative Commons Attribution-NoDerivs License](http://creativecommons.org/licenses/by-nd/3.0/)
  * Double-J Design, [Siena Icon Pack](http://www.doublejdesign.co.uk/products-page/icons/siena/)

- [Creative Commons Attribution-Noncommercial-Share Alike License](http://creativecommons.org/licenses/by-nc-sa/3.0/) (with explicit permission for use in WebPutty)
  * Hayes Roberts, [www.bluebison.net](http://www.bluebison.net/content/?p=786)

# License

WebPutty is licensed under the [MIT](http://www.opensource.org/licenses/mit-license.php "Read more about the MIT license form") license.
