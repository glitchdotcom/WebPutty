;head(function() {
    $('#btn-feedback').click(function(e) {
        e.preventDefault();
        $('#dlg-feedback').modal({
            overlayId: 'modal-overlay',
            overlayCss: {background: '#000', opacity: 0.7},
            overlayClose: true
        });
    });

    $('.btn-set-locale').click(function(e) {
        e.preventDefault();
        $('#dlg-locale').modal({
            overlayId: 'modal-overlay',
            overlayCss: {background: '#000', opacity: 0.7},
            overlayClose: true,
            onShow: function(dialog) {
                dialog.container.css({width: 'auto', height: 'auto'});
            }
        });
    });

    $('#dlg-locale input[type="submit"]').live('click', function(e) {
        $(this).closest('form').find('.throbber').fadeTo('fast', 1);
    });

    $('.youtube-placeholder').live('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var videoId = $(this).attr('href').substr(-11);
        var iframe = $('<iframe class="youtube-player" width="530" height="330" src="http://www.youtube.com/embed/' + videoId + '?autoplay=1&hd=1" frameborder="0" allowfullscreen></iframe>');
        $(this).replaceWith(iframe);
    });
});
