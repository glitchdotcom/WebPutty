;head(function(){
    $('.tweet').first().addClass('first-tweet center-tweet').removeClass('right-tweet');
    $('.tweet').last().prev().addClass('last-tweet');

    $('.say-what-control').live('click', function(e){
        e.preventDefault();
        var current_tweet = $('.tweet.center-tweet');

        if ($(this).hasClass('next')) {
            $('.tweets').animate({'margin-left': '-=960'}, 300);
            next_tweet = current_tweet.next().next().addClass('center-tweet').removeClass('right-tweet');
            current_tweet.addClass('left-tweet');
        } else if ($(this).hasClass('prev')) {
            $('.tweets').animate({'margin-left': '+=960'}, 300);
            prev_tweet = current_tweet.prev().prev().addClass('center-tweet').removeClass('left-tweet');
            current_tweet.addClass('right-tweet');
        };

        current_tweet.removeClass('center-tweet');

        $('.say-what-control.prev').show();
        $('.say-what-control.next').show();

        if ($('.tweet.first-tweet').hasClass('center-tweet')) {
            $('.say-what-control.prev').hide();
        };

        if ($('.tweet.last-tweet').hasClass('center-tweet')) {
            $('.say-what-control.next').hide();
        };
    });

    $('.say-what-control.prev').hide();
});
