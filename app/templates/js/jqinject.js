;(function() {
    var _jq = window._jq = null;
    Logger.log('jqinject', 'loading jQuery...');
    if (typeof(jQuery) !== 'undefined') {
        Logger.log('jqinject', 'jQuery is already loaded');
        _jq = window._jq = jQuery;
        return;
    }

    var script = document.createElement('script');
    script.src = '{{ jquery_url }}';
    var head = document.getElementsByTagName('head')[0];
    var done = false;
    // Attach handlers for all browsers
    script.onload = script.onreadystatechange = function(){
        if ( !done && (!this.readyState
                || this.readyState == 'loaded'
                || this.readyState == 'complete') ) {
            done = true;
            if (jQuery) {
                Logger.log('jqinject', 'jQuery loaded');
                _jq = window._jq = jQuery.noConflict(true);
            } else {
                Logger.log('jqinject', 'jQuery failed to load');
            }
            script.onload = script.onreadystatechange = null;
            head.removeChild(script);
        }
    };
    head.appendChild(script);
})();
