;head(function(){
    var fixedWidthTextInput = function() {
        // set to 100% width (so it's as wide as the widest URL).
        $('#newPreviewUrl').css('width', '100%');
        // now make it static width so that if you edit the long url, things don't shrink
        $('#newPreviewUrl').css('width', $('#newPreviewUrl').width() + 'px');
    };
    fixedWidthTextInput();

    $('#btn-configure').click(function(e, fFocusAddUrl) {
        e.preventDefault();
        var url = $(this).attr('href');
        var dlg = $('#dlg-editpage');
        dlg.modal({
            overlayId: 'modal-overlay',
            overlayCss: {background: '#000', opacity: 0.7},
            overlayClose: true,
            onOpen: function(dialog) {
                dlg.load(url, function() {
                    dialog.data.show();
                    dialog.container.resize();
                    dialog.container.fadeIn('fast');
                    fixedWidthTextInput();
                    if (fFocusAddUrl) {
                        dlg.find('#newPreviewUrl').focus();
                    }
                });
                dialog.overlay.fadeIn('fast');
            }
        });
    });

    $('#dlg-editpage .click-to-edit-text, .editpage .click-to-edit-text').live('click', function(e) {
        e.preventDefault();
        var $this = $(this);
        var this_id = this.id;
        var input_id = this_id.substr(this_id.indexOf('_') + 1);

        // swap the hidden input for a text input
        $('<input>')
        .attr({
            type: 'text',
            value: $this.text(),
            name: input_id,
            id: input_id,
            'class': 'click-to-edit input_full'
        })
        .replaceAll($('#' + input_id))
        .focus()
        .bind('blur', function(e) {
            // hide the text input on blur
            var newUrl = $(this).val();
            $('<input>')
            .attr({
                type: 'hidden',
                value: newUrl,
                name: input_id,
                id: input_id
            })
            .replaceAll($('#' + input_id));
            $('#' + this_id).text(newUrl).show();
        });
        $this.hide();
        return false;
    });

    $('#dlg-editpage .removeUrl, .editpage .removeUrl').live('click', function(e) {
        e.preventDefault();
        $(this).parents('tr').remove();
    });

    $('#newPreviewUrl').live('keypress', function(e) {
        // redirect enter to the add url button
        if (e.which === 13) {
            e.preventDefault();
            $('.addUrl').click();
        }
    });

    $('#dlg-editpage .addUrl, .editpage .addUrl').live('click', function(e) {
        e.preventDefault();
        var $input = $('#newPreviewUrl');
        var newUrl = $input.val();

        if (newUrl.toLowerCase() === 'http://') {
            $input.select();
            return;
        }

        if (!(newUrl.toLowerCase().indexOf('http://') === 0 || newUrl.toLowerCase().indexOf('https://') === 0)) {
            newUrl = 'http://' + newUrl;
        }

        var newIx = 0;
        var trailingIx = /\d+$/;
        $('input[id^="preview_urls-"]').each(function(ix, el){
            var ix = parseInt(trailingIx.exec(el.id));
            if (ix > newIx) newIx = ix;
        });
        newIx++;

        $.tmpl(
            '<tr><td><a href="#" id="text_preview_urls-${newIx}" class="click-to-edit-text" title="Click to edit">${newUrl}</a><input type="hidden" id="preview_urls-${newIx}" name="preview_urls-${newIx}" value="${newUrl}" /></td><td><button class="removeUrl">Remove URL</button></td></tr>',
            {
                newUrl: newUrl,
                newIx: newIx
            }
        )
        .insertBefore($(this).parents('tr'));
        fixedWidthTextInput();

        $input.val('http://').select();
    });

    // only do ajaxy-submit on the dialog version
    $('#dlg-editpage input[type="submit"]').live('click', function(e) {
        e.preventDefault();
        var $this = $(this);
        var $form = $this.closest('form');
        $form.find('.errors').remove();
        $form.find('.throbber').fadeTo('fast', 1);
        $.post($form.attr('action'), $form.serialize(), function(data) {
            $form.find('.throbber').fadeTo('fast', 0);
            if (data === 'OK') {
                Editor.updatePageDetails($('#name').val(), $('#url').val(), $('input[id^="preview_urls-"]'));
                $.modal.close();
            } else {
                $(data)
                .hide()
                .appendTo($form)
                .fadeIn();
            }
        });
    });
});
