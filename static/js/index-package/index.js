;head('jquery', function() {
        $(function() {
            $('img[data-lazyload]').each(function(i, e) {
            var $e = $(e);
            var $page = $e.parent().parent().parent();
            var delay = $page.index() * 100;
            setTimeout(function() { $e.attr('src', $e.attr('data-lazyload')); }, delay);
        });
    });
});

head(function() {
    $('#new-site').click(function(e) {
        e.preventDefault();
        var url = $(this).find('a.new-site').attr('href');
        var dlg = $('<div>')
            .attr({ 'id': 'dlg-newsite', 'class': 'dlg'})
            .css('display', 'none');
        dlg.modal({
            overlayId: 'modal-overlay',
            overlayCss: {background: '#000', opacity: 0.7},
            overlayClose: true,
            onOpen: function(dialog) {
                dlg.load(url, function() {
                    dialog.data.show();
                    dialog.container.resize();
                    dialog.container.fadeIn('fast');
                });
                dialog.overlay.fadeIn('fast');
            }
        });
    });

    $('#dlg-newsite input[type="submit"]').live('click', function(e) {
        e.preventDefault();
        var $this = $(this);
        var $form = $this.closest('form');
        $form.find('.errors').remove();
        $form.find('.throbber').fadeTo('fast', 1);
        $.post($form.attr('action'), $form.serialize(), function(data) {
            if (data.type === 'success') {
                window.location.href = data.redirect;
            } else {
                $form.find('.throbber').fadeTo('fast', 0);
                $(data.errors)
                .hide()
                .appendTo($form)
                .fadeIn();
            }
        });
    });

    var getId = function(node) {
        var sDomId = node.attr('id');
        return sDomId.substr(sDomId.indexOf('-') + 1);
    };

    $('.new-page').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        var url = $(this).attr('href');
        var dlg = $('<div>')
            .attr({ 'id': 'dlg-newpage', 'class': 'dlg'})
            .css('display', 'none');
        dlg.modal({
            overlayId: 'modal-overlay',
            overlayCss: {background: '#000', opacity: 0.7},
            overlayClose: true,
            onOpen: function(dialog) {
                dlg.load(url, function() {
                    dialog.data.show();
                    dialog.container.resize();
                    dialog.container.fadeIn('fast');
                });
                dialog.overlay.fadeIn('fast');
            },
            onClose: function(dialog) {
                $.modal.close();
            }
        });
    });

    $('#dlg-newpage input[type="submit"]').live('click', function(e) {
        e.preventDefault();
        var $this = $(this);
        var $form = $this.closest('form');
        $form.find('.errors').remove();
        $form.find('.throbber').fadeTo('fast', 1);
        $.post($form.attr('action'), $form.serialize(), function(data) {
            if (data.type === 'success') {
                window.location.href = data.redirect;
            } else {
                $form.find('.throbber').fadeTo('fast', 0);
                $(data.errors)
                .hide()
                .appendTo($form)
                .fadeIn();
            }
        });
    });

    $('.configure-site').click(function(e) {
        e.preventDefault();
        var url = $(this).attr('href');
        var dlg = $('<div>')
            .attr({ 'id': 'dlg-editsite', 'class': 'dlg'})
            .css('display', 'none');
        dlg.modal({
            overlayId: 'modal-overlay',
            overlayCss: {background: '#000', opacity: 0.7},
            overlayClose: true,
            onOpen: function(dialog) {
                dlg.load(url, function() {
                    dialog.data.show();
                    dialog.container.resize();
                    dialog.container.fadeIn('fast');
                });
                dialog.overlay.fadeIn('fast');
            }
        });
    });

    $('#dlg-editsite input[type="submit"]').live('click', function(e) {
        e.preventDefault();
        var $this = $(this);
        var $form = $this.closest('form');
        $form.find('.errors').remove();
        $form.find('.throbber').fadeTo('fast', 1);
        $.post($form.attr('action'), $form.serialize(), function(data) {
            $form.find('.throbber').fadeTo('fast', 0);
            if (data === 'OK') {
                $('.site-name:visible').text($('#name').val());
                $.modal.close();
            } else {
                $(data)
                .hide()
                .appendTo($form)
                .fadeIn();
            }
        });
    });

    $('a.site-setting-control.users').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        var url = $(this).attr('href');
        var dlg = $('<div>')
            .attr({ 'id': 'dlg-siteusers', 'class': 'dlg'})
            .css('display', 'none');
        dlg.modal({
            overlayId: 'modal-overlay',
            overlayCss: {background: '#000', opacity: 0.7},
            overlayClose: true,
            onOpen: function(dialog) {
                dlg.load(url, function() {
                    dialog.data.show();
                    dialog.container.resize();
                    dialog.container.fadeIn('fast');
                });
                dialog.overlay.fadeIn('fast');
            },
            onClose: function(dialog) {
                $.modal.close();
            }
        });
    });
    
    $('a.site-setting-control.leave').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        var site_id = getId($(this).parents('.site:first'));
        var msg = "Taking off so soon?\n\nAre you sure you want to remove yourself from this site?\n\nYou will not be able to view or edit any of the styles.";
        if(confirm(msg)){
            $.post(
                Urls['leave_site'],
                {site_id: site_id},
                function(data) {
                    // site layout is complicated (temp divs, etc.) so just refresh the page
                    window.location.reload();
                }
            );
        }
    });

    $('a.site-setting-control.delete').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        var site_id = getId($(this).parents('.site:first'));
        var msg = "Holy crap-balls!\n\nAre you sure you want to permanently delete this site and ALL of its stylesheets?\n\nAll at once? Really?";
        if(confirm(msg)){
            $.post(
                Urls['delete_site'],
                {site_id: site_id},
                function(data) {
                    // site layout is complicated (temp divs, etc.) so just refresh the page
                    window.location.reload();
                }
            );
        }
    });

    $('.page a.delete').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        var $page = $(this).parents('.page:first');
        var lastStyle = ($page.siblings().length === 1);
        var msg = "Are you sure you want to permanently delete this stylesheet?\n\nI mean, what's it ever done to you?";
        if (lastStyle) {
            msg = "HOLY CRAP-BALLS ALERT: Deleting this stylesheet will also delete this entire site!\n\n" + msg;
        }
        if(confirm(msg)){
            var url = '';
            var data = {};
            var toDelete = {};
            var fRefresh = false;

            if (lastStyle) {
                var site_id = getId($page.parents('.site:first'));
                url = Urls['delete_site'];
                data = {site_id: site_id};
                toDelete = '#site-' + site_id;
                // site layout is complicated (temp divs, etc.) so just refresh the page
                fRefresh = true;
            } else {
                var page_id = getId($page);
                url = Urls['delete_page'];
                data = {page_id: page_id};
                toDelete = '#page-' + page_id;
            }

            $.post(
                url,
                data,
                function(data) {
                    if (fRefresh) {
                        window.location.reload();
                    } else {
                        // collapse the expanded site so
                        // page layout ordering is repaired
                        $('body.viewing').click();
                        $(toDelete).remove();
                    }
                }
            );
        }
    });
});
