;(function(window, document, undefined) {
    {% include 'js/comm.js' %}
    var pageKey = '{{ page_key }}';
    var comm = new Comm(pageKey);
    var getLinkTag = function() {
        // we still look by id b/c the live-preview uses a style tag
        var style = document.getElementById(pageKey);
        if (style) {
            return style;
        } else {
            var tags = document.getElementsByTagName('link');
            for(var ix = 0; ix < tags.length; ix++) {
                if (tags[ix].getAttribute('href').indexOf(pageKey) > -1){
                    Logger.log('iframe', ['found matching link tag (by href)', pageKey]);
                    return tags[ix];
                }
            }
            Logger.log('iframe', ["couldn't find a matching link/style tag...page/style key mismatch?", pageKey]);
            return null;
        }
    };
    var firebugEmbedded = false;
    var customizeFirebugLite = function() {
        var hideFirebugButton = false;
        var hideDeactivateButton = true;
        var hideOtherPanels = false;

        if (!(Firebug && Firebug.chrome && Firebug.chrome.document)) {
            setTimeout(customizeFirebugLite, 50);
            return;
        }

        var doc = Firebug.chrome.document;

        if (hideFirebugButton) {
            var fbButton = doc.getElementById('fbFirebugButton');
            fbButton.style.display = 'none';
        }

        if (hideDeactivateButton) {
            // there's no way to re-activate the Firebug Lite window after it's been deactivated
            // (that i've been able to find anyway), so let's just hide that option altogether :)
            var btDeactivate = doc.getElementById('fbWindow_btDeactivate');
            btDeactivate.style.display = 'none';
        }

        if (hideOtherPanels) {
            // select a panel that's sticking around before we start hiding things
            Firebug.chrome.selectPanel('HTML');
            doc.getElementById('fbConsoleTab').style.display = 'none';
            doc.getElementById('fbScriptTab').style.display = 'none';
            doc.getElementById('fbDOMTab').style.display = 'none';
        }
        Logger.log('iframe', ['finished customizing Firebug Lite', pageKey]);
    };
    if (window != window.top) {
        {% include 'js/jqinject.js' %}
        comm.receiveMessage('iframe', '{{ request.host_url[:-1] }}', {
            ready: function(data) {
                comm.sendMessage('iframe', 'ready', { href: window.location.href });
            },
            printLog: function(data) {
                Logger.printHistory(data);
            },
            update: function(data) {
                var style = getLinkTag();
                if (!style) {
                    comm.sendMessage('iframe', 'missing_style_tag', { href: window.location.href });
                    return;
                }
                var head = style.parentNode; // May not actually be <head>
                style.id = '';
                new_style = document.createElement('style');
                new_style.id = pageKey;
                new_style.type = 'text/css';
                if (new_style.styleSheet) {
                    new_style.styleSheet.cssText = data;
                } else {
                    new_style.innerHTML = data;
                }
                head.appendChild(new_style);
                head.removeChild(style);
            },
            highlight: function(data) {
                _jq('#css_editor_highlight_container').remove();
                selectors = data.selectors;
                if (!selectors || !selectors[0]) {
                    Logger.log('iframe', ['got empty selector', pageKey]);
                    return;
                }
                var j = _jq(selectors[0]);
                for (var i = 1; i < selectors.length; i++ ) {
                    j = j.find(selectors[i]);
                }
                var container = _jq('<div id="css_editor_highlight_container">');
                j.each(function(i, e) {
                    var self = _jq(e);
                    var offset = self.offset();
                    var top = offset.top;
                    var left = offset.left;
                    var width = self.width();
                    var height = self.height();
                    var padding  = [self.css('padding-top'),
                                    self.css('padding-right'),
                                    self.css('padding-bottom'),
                                    self.css('padding-left')];
                    var margin  = [self.css('margin-top'),
                                   self.css('margin-right'),
                                   self.css('margin-bottom'),
                                   self.css('margin-left')];
                    var border  = [self.css('border-top-width'),
                                   self.css('border-right-width'),
                                   self.css('border-bottom-width'),
                                   self.css('border-left-width')];
                    var marginTop = margin[0].match(/^(\d+(\.\d+)?)px$/);
                    if (marginTop && Number(marginTop[1])) {
                        top -= Number(marginTop[1]);
                    }
                    var marginLeft = margin[3].match(/^(\d+(\.\d+)?)px$/);
                    if (marginLeft && Number(marginLeft[1])) {
                        left -= Number(marginLeft[1]);
                    }
                    var inner = _jq('<div>').css({
                                    width: width,
                                    height: height,
                                    margin: border.join(' '),
                                    border: '0 solid SlateBlue',
                                    borderWidth: padding.join(' '),
                                    backgroundColor: 'SkyBlue'
                                });
                    var outer = _jq('<div>').css({
                                    opacity: 0.8,
                                    top: top,
                                    left: left,
                                    backgroundColor: '#f99',
                                    zIndex: 2147483647,
                                    border: '0 solid #EDFF64',
                                    borderWidth: margin.join(' '),
                                    position: 'absolute'
                                });
                    inner.appendTo(outer);
                    outer.appendTo(container);
                });
                container.appendTo('body');
            },
            firebug: function(data) {
                if (data && !firebugEmbedded) {
                    Logger.log('iframe', ['adding Firebug Lite...', pageKey]);
                    var script = document.createElement('script');
                    script.src = 'https://getfirebug.com/firebug-lite.js#startOpened,disableWhenFirebugActive=false';
                    var head = document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0];
                    script.onload = script.onreadystatechange = function(){
                        if ( !firebugEmbedded && (!this.readyState
                                || this.readyState == 'loaded'
                                || this.readyState == 'complete') ) {
                            firebugEmbedded = true;
                            script.onload = script.onreadystatechange = null;
                            head.removeChild(script);
                            Logger.log('iframe', ['Firebug Lite loaded', pageKey]);
                            customizeFirebugLite();
                        }
                    };
                    head.appendChild(script);
                } else {
                    Logger.log('iframe', ['Firebug Lite already loaded, so re-open if closed', pageKey]);
                    Firebug.chrome.open();
                }
            }
        });
        comm.sendMessage('iframe', 'ready', { href: window.location.href });
    } else { 
        Logger.log('iframe', ['top window, no one to talk to', pageKey]);
        if (window.location.search.indexOf('__preview_css__') !== -1) {
            Logger.log('iframe', ['__preview_css__ set in query string, so updating link tag...', pageKey]);
            var style = getLinkTag();
            if (!style) return;
            style.href = '{{ preview_url }}';
        }
    }
})(window, document);
