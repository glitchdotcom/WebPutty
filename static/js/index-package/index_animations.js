;head(function () {
    var hasHistory = !!(window.history && window.history.pushState);
    var leftOffset = 0;
    var topOffset = 0;
    var leftMargin = parseInt($("#content").css("margin-left"));
    var topMargin = parseInt($("#content").css("margin-top")) + $("#header").outerHeight(true);
    var goingBack = false;

    var pushState = function() {}; // Assume noop;

    $(".site.compacted").live("click", function(e) {
        if ($(this).attr('id') == 'new-site') return;

        e.stopPropagation();
        e.preventDefault();

        var $site = $(this);
        var $pages = $site.find(".pages");

        if (!goingBack) {
            pushState(Urls.site.replace('/0', '/' + $site.attr('data-id')));
        }

        // Expand the pages
        $("body").addClass("viewing");

        var $pageCollection = $pages.find(".page");
        var pageCount = $pageCollection.size();

        var columnWidth = $pageCollection.first().outerWidth(true);
        var rowHeight = $pageCollection.first().outerHeight(true);
        // use the outer width (including margins) of #content b/c visually,
        // that's the space we have to work with
        var windowWidth = $("#content").outerWidth(true);
        var columnCount = (Math.floor(windowWidth / columnWidth));

        // Save the distance of this .site from the top left of #content
        // We'll use this when we re-compact the site to animate it back
        // to the right spot.
        leftOffset = $site.offset().left;
        topOffset = $site.offset().top;

        // Runs only after all pages have been animated out to their grid position
        var addShadows = _.after(pageCount, function() {
            $site.addClass("expanded");
            $('#site-bg').css('opacity', 1);
        });

        $site.siblings().addClass("hide");

        // create a temp .site element to hold the place of the expanding site
        // when we make it position absolute. We'll dump the children of the
        // absolutely positioned site into this container when the compact
        // animation is done.
        var $temp = $site.clone();
        $temp.addClass('temp')
             .attr('id', 'temp-' + $site.attr('id'))
             .empty();
        $site.after($temp);

        $site.css({
            left: leftOffset - leftMargin,
            top: topOffset - topMargin
        }).removeClass("compacted");

        var numRows = Math.ceil($pageCollection.length / columnCount);
        var boundingHeight = numRows * rowHeight + topMargin + 10;
        $('#site-bg').css('height', boundingHeight);

        var row = 0;
        var column = 0;
        $site.animate({
                left: 0,
                top: 0
            }, 250,
            function() {
                $.each($pageCollection, function() {
                    $(this).animate({
                        left: columnWidth * column,
                        top: rowHeight * row,
                        }, 100,
                        addShadows
                    );

                    column ++;
                    if (column >= columnCount) {
                        column = 0;
                        row++;
                    }
                });
            }
        );
    });

    function compactExpandedSite(e) {
        // don't collapse things unless it makes sense to
        var $target = $(e.target);
        if (
            $target.is('a') ||
            $target.is('button') ||
            $target.is('input[type="submit"]') ||
            $target.is('img') || // page preview image
            $target.parents('#simplemodal-container').length > 0 ||
            $target.is('div') &&
                (
                    $target.attr('id') === 'header' ||
                    $target.attr('id') === 'footer' ||
                    $target.attr('id') === 'modal-overlay' ||
                    $target.attr('id') === 'guider_overlay'
                )
           ) { return; }

        var $site = $(".expanded");

        if ($site.length) {
            $("body.viewing").removeClass("viewing");

            var $pages = $site.find(".pages");
            var $pageCollection = $pages.find(".page");
            var pageCount = $pageCollection.size();

            // Runs only after all pages have been animated back into the pile
            var showSiblings = _.after(pageCount, function() {
                $site.animate({
                    left: leftOffset - leftMargin,
                    top: topOffset - topMargin
                    }, 100,
                    function() {
                        _.delay(function() {
                            $temp = $(".site.temp")
                            $temp.removeClass("hide").prepend($site.children());
                            var id = $site.attr('id');
                            $site.remove();
                            $temp.attr('id', id);
                            $(".site").not($temp).removeClass("hide");
                            $temp.removeClass("temp");
                        }, 25);
                    }
                );
            });

            $('#site-bg').css('opacity', 0);

            $site.removeClass("expanded");
            $.each($pageCollection, function() {
                $(this).animate({
                    left: 0,
                    top: 0
                    }, 100,
                    showSiblings
                );
            });
        }
    }

    $('body.viewing').live("click", function(e) {
        pushState(Urls.index);
        compactExpandedSite(e);
    });

    $(document).keydown(function(e) {
        // don't collapse things if a SimpleModal
        // dialog or guider is visible
        if (
            e.keyCode === 27 &&
            !$('#modal-overlay').is(':visible') &&
            !$('#guider_overlay').is(':visible')
           ) {
            pushState(Urls.index);
            compactExpandedSite(e);
        }
    });

    if (hasHistory) {
        pushState = function(url) {
            window.history.pushState(null, '', url);
        };
        window.onpopstate = function(e) {
            goingBack = true;
            var m = null;
            if ((m = window.location.href.match(/\/site\/(\d+)/))) {
                $('#site-' + m[1]).click();
            }
            else {
                compactExpandedSite($('body')[0]);
            }
            goingBack = false;
        };
        window.onpopstate();
    }
});
