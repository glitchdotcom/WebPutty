;(function(window, document, undefined) {
    window.Logger = window.Logger || (function () {
        var storage = window.localStorage;
        var enabled = storage ? storage['loggers'] ? JSON.parse(storage['loggers']) : {} : {};
        var historyMap = {};
        var logHistory = true;

        {% if debug %}if (typeof(enabled['all']) === 'undefined') enabled['all'] = true;{% endif %}

        var save = function() {
            if (storage) {
                storage['loggers'] = JSON.stringify(enabled);
            }
        };

        var print = function(args) {
            if (typeof(console) === "undefined" || !console.log) return;
            console.log(args);
        };

        var addToHistory = function(region, args) {
            if (!logHistory) return;

            if (!historyMap[region]) {
                historyMap[region] = [];
            }
            historyMap[region].push(args);

            // everything gets logged to 'all'
            if (region !== 'all') {
                if (!historyMap['all']) {
                    historyMap['all'] = [];
                }
                historyMap['all'].push(args);
            }
        };

        var isArray = function(value) {
            return Object.prototype.toString.apply(value) === '[object Array]';
        };

        var keys = function(value) {
            var keys = [];
            for (var key in value) {
                if (value.hasOwnProperty(key)) {
                    keys[keys.length] = key;
                }
            }
            return keys;
        };

        var self = {
            log: function (region) {
                var isRegionEnabled = false;
                var args;

                if (arguments.length === 1) {
                    isRegionEnabled = true;
                    args = Array.prototype.slice.call(arguments);
                    region = 'all';
                } else {
                    isRegionEnabled = enabled['all'] || enabled[region] || false;
                    args = Array.prototype.slice.call(arguments, 1);
                }

                if (isRegionEnabled) {
                    if (args.length === 1 && isArray(args[0])) {
                        args = args[0];
                    }
                    args.unshift(region);
                    print(args);
                }

                addToHistory(region, args);
            },

            enable: function (region) {
                region = region || 'all';
                enabled[region] = true;
                save();
            },

            disable: function (region) {
                region = region || 'all';
                delete enabled[region];
                save();
            },

            disableAll: function () {
                enabled = {};
                enabled['all'] = false;
                save();
            },

            enableAll: function () {
                enabled['all'] = true;
                save();
            },

            printHistory: function (region) {
                region = region || 'all';
                for (var i = 0; i < historyMap[region].length; i++) {
                    print(historyMap[region][i]);
                }
            },

            list: function () {
                print(keys(historyMap));
            }
        };

        return self;
    })();
})(window, document);
