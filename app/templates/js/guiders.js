;(function(window, document, undefined) {
    var mark_seen = function(guider_name) {
        $.post(Urls['saw_guider'], {guider_name: guider_name});
    };

    var show_guider = window.show_guider = function(guider_name, is_first) {
        var close_guider = function() {
            guiders.hideAll();
            if ($('#guider_' + guider_name).length) {
                guiders.createGuider({
                    attachTo: '#guider_' + guider_name,
                    buttons: [],
                    title: '{% trans %}No problem!{% endtrans %}',
                    description: '{% trans %}Want to see the tutorial later? Just click here{% endtrans %}',
                    id: 'hide',
                    position: 7,
                    width: 250
                }).show();
                setTimeout(guiders.hideAll, 2000);
            }
        };

        var do_mark_seen = function(func) {
            return function() {
                mark_seen(guider_name);
                func();
            };
        };

        var leave_tour = {
            name: '{% trans %}Leave Tour{% endtrans %}',
            classString: 'quiet',
            onclick: close_guider
        }

        switch (guider_name) {
            case 'index_intro':
                guiders.createGuider({
                    buttons: [
                        {name: '{% trans %}No Thanks{% endtrans %}', onclick: do_mark_seen(close_guider), classString: 'quiet'}, 
                        {name: '{% trans %}Sure!{% endtrans %}', onclick: do_mark_seen(guiders.next)}
                    ],
                    title: '{% trans %}Welcome to {{ appname }}!{% endtrans %}',
                    description: '{% trans %}{{ appname }} helps you write, update, and publish the CSS for your websites as fast as you can write it.<br /><br />Would you like a quick tour?{% endtrans %}',
                    id: 'g1',
                    next: 'g2',
                    width: 300,
                    overlay: true
                }).show();

                guiders.createGuider({
                    attachTo: '.site:first .page:first',
                    buttons: [leave_tour, {
                        name: '{% trans %}Next{% endtrans %}',
                        onclick: function() {
                            guiders.hideAll();
                            $('.site:first .page').click();
                            _.delay(guiders.next, 500);
                        }
                    }],
                    title: '{% trans %}Your Sites{% endtrans %}',
                    description: '{% trans %}Each of your websites is shown on the home page as a pile of stylesheets. Clicking a site expands it to show the stylesheets it contains.{% endtrans %}',
                    id: 'g2',
                    next: 'g3',
                    position: 3,
                    width: 300
                });

                var attachTo = '.site:first .page:not(.new):last';
                guiders.createGuider({
                    attachTo: attachTo,
                    buttons: [leave_tour, {name: '{% trans %}Next{% endtrans %}', onclick: function() {
                        $link = $(attachTo).find('a:first');
                        window.location.href = $link.attr('href') + '?__on_tour__';
                        return false;
                    }}],
                    title: '{% trans %}Stylesheets{% endtrans %}',
                    description: '{% trans %}Stylesheets are what contain the actual styles used by your website. A website can contain multiple stylesheets, and each stylesheet can be included on multiple pages (e.g. a site-wide style on your base template).<br /><br />When you create a stylesheet we ask you for a URL that uses that stylesheet so we can show you a preview image here.{% endtrans %}',
                    id: 'g3',
                    next: 'g4',
                    position: 4,
                    width: 300
                });
                break;
            case 'editor_intro':
                guiders.createGuider({
                    buttons: [
                        {name: '{% trans %}Leave Tour{% endtrans %}', onclick: do_mark_seen(close_guider), classString: 'quiet'}, 
                        {name: '{% trans %}Next{% endtrans %}', onclick: do_mark_seen(guiders.next)}
                    ],
                    title: '{% trans %}Stylesheet Editor{% endtrans %}',
                    description: '{% trans %}This is the transmogrifier. It allows you to edit your website\'s CSS on one half of the screen (well, <a href="http://sass-lang.com/" target="_blank">SCSS</a>, technically speaking) and see how those changes will affect your website on the other...in real-time!{% endtrans %}',
                    id: 'g1',
                    next: 'g2',
                    width: 300,
                    overlay: true
                }).show();

                guiders.createGuider({
                    attachTo: '#version-controls select',
                    buttons: [leave_tour, {name: '{% trans %}Next{% endtrans %}', onclick: guiders.next}],
                    title: '{% trans %}Stylesheet Modes{% endtrans %}',
                    description: "{% trans %}Every stylesheet in {{ appname }} has two modes: a preview mode and a published mode.<br /><br /><b>Preview mode</b> gives you a sandbox to play in without inflicting half-baked changes on your visitors.<br /><br />You can quickly switch between these two modes using this menu.{% endtrans %}",
                    id: 'g2',
                    next: 'g3',
                    position: 6,
                    width: 300
                });

                guiders.createGuider({
                    attachTo: '#btn-publish',
                    buttons: [leave_tour, {name: '{% trans %}Next{% endtrans %}', onclick: guiders.next}],
                    title: '{% trans %}Sharing the sexy{% endtrans %}',
                    description: "{% trans %}When your changes are fully baked and ready, you can publish them with the click of a button!{% endtrans %}",
                    id: 'g3',
                    next: 'g4',
                    position: 9,
                    width: 300
                });

                guiders.createGuider({
                    buttons: [{name: "{% trans %}Let me at that (S)CSS!{% endtrans %}", onclick: guiders.hideAll}],
                    title: '{% trans %}Start CSS-es-es-esing!{% endtrans %}',
                    description: '{% trans %}There are a bunch of other nifty features in {{ appname }}, but at this point you\'ve probably got enough of the idea to get started.<br /><br />Thanks, and have fun CSS-es-es-esing!{% endtrans %}',
                    id: 'g4',
                    width: 300,
                    overlay: true
                });

                break;
        }
    };
})(window, document);
