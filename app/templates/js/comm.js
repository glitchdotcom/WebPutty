{% include 'js/console.js' %}
{% include 'js/xd.js' %}

if (!Comm) {
    var Comm = function(pageKey) {
        this.pageKey = pageKey;
    }

    Comm.prototype.sendMessage = function(name, command, data, target) {
        target = target || window.parent;
        var obj = {
                pageKey: this.pageKey,
                command: command,
                data: data
            };
        var msg = JSON.stringify(obj);
        Logger.log('comm', [name, 'send', msg, this.pageKey]);
        XD.postMessage(msg, '*', target);
    };

    Comm.prototype.receiveMessage = function(name, domain, commandHandlers) {
        var self = this;
        XD.receiveMessage(function(e) {
            Logger.log('comm', [name, 'receive', e.data, self.pageKey]);
            try {
                var obj = JSON.parse(e.data);
                if (!obj || typeof(obj) !== 'object') {
                    Logger.log('comm', [name, 'missing command object', e.data, self.pageKey]);
                    return;
                }
                if (obj.pageKey !== self.pageKey) {
                    Logger.log('comm', [name, 'received bogus message (mismatching page keys)', self.pageKey]);
                    return;
                }
                if (obj.command && typeof(commandHandlers[obj.command]) === 'function') {
                    commandHandlers[obj.command](obj.data);
                }
            } catch (err) {
                Logger.log('comm', [name, 'error parsing data', err, e.data, self.pageKey]);
            }
        }, domain);
    };
}
