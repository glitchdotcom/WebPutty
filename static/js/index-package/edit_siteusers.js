;head(function(){
    $('.removeAdmin,.removeUser').live('click', function(e) {
        e.preventDefault();
        $this = $(this);
        var $form = $this.closest('form');
        var fAdminOnly = $this.hasClass('removeAdmin');
        var msg = 'Are you sure you want to remove this ' + (fAdminOnly ? "user's admin privileges?" : "user entirely?");
        if(confirm(msg)){
            var user_id = $this.parents('tr:first').attr('data-user');
            var data = {user_id: user_id};
            if (fAdminOnly) {
                data['remove_admin_only'] = 1;
            }
            $this.attr('disabled', 'disabled');
            $.post(
                Urls['remove_user'],
                data,
                function(data) {
                    var rows = $form.find('[data-user="' + user_id + '"]');
                    if (fAdminOnly) {
                        rows = rows.filter('[data-role="admin"]');
                    }
                    rows.remove();
                }
            );
        }
    });

    $('#dlg-siteusers input[type="submit"]').live('click', function(e) {
        e.preventDefault();
        var $this = $(this);
        var $form = $this.closest('form');
        $form.find('.flash').remove();
        $form.find('.throbber').fadeTo('fast', 1);
        $.post($form.attr('action'), $form.serialize(), function(data) {
            $form.find('.throbber').fadeTo('fast', 0);
            var msg = null;
            if (data === 'OK') {
                msg = $('<td class="flash flash-success">').text('Invitation sent!');
                $form.find('input[type="text"]').val('');
                $form.find('input[type="checkbox"]').attr('checked', false);
                _.delay(function() { msg.fadeOut(); }, 2000);
            } else {
                msg = $('<td class="flash flash-error">').text(data);
            }
            msg.wrap('<tr>').hide();
            $form.find('table').append(msg);
            msg.fadeIn();
        });
    });
});
