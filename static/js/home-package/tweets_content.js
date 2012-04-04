;head(function(){
    var tweets = tweet_data.sort(function() { return 0.5 - Math.random() }); // randomize
    //var tweets = tweet_data;
    var tweet_html = [];

    for (i=0; i<tweets.length; i++){
        var obj = tweets[i];
        var urls = obj.entities.urls;
        var hashtags = obj.entities.hashtags;
        var user_mentions = obj.entities.user_mentions;

        var ents = [];

        if (urls.length > 0) {
            for (u=0; u<urls.length; u++) {
                var url = urls[u];
                var ent = [];

                ent.indices = url.indices;
                ent.index_diff = url.indices[1] - url.indices[0];
                if (url.display_url) {
                    var use_url = url.display_url;
                } else {
                    var use_url = url.url;
                };
                ent.html = '<a target="_blank" href="'+ url.url +'">'+ use_url +'</a>';
                ents.push(ent);
            };
        };

        if (hashtags.length > 0) {
            for (h=0; h<hashtags.length; h++){
                var tag = hashtags[h];
                var ent = [];

                ent.indices = tag.indices;
                ent.index_diff = tag.indices[1] - tag.indices[0];
                var text = tag.text;
                var indices = tag.indices;
                ent.html = '<a target="_blank" href="http://www.twitter.com/search/?q='+ text +'">#'+ text +'</a>';
                ents.push(ent);
            };
        };

        if (user_mentions.length > 0) {
            for (m=0; m<user_mentions.length; m++){
                var user = user_mentions[m];
                var ent = [];

                ent.indices = user.indices;
                ent.index_diff = user.indices[1] - user.indices[0];
                ent.html = '<a target="_blank" href="http://www.twitter.com/'+ user.screen_name +'">@'+ user.screen_name +'</a>';
                ents.push(ent);
            };
        };

        ents.sort(
            function(a,b) {
                return parseFloat(a.indices[0]) - parseFloat(b.indices[0]);
            }
        );

        // If entities, manipulate tweet text. Otherwise use text from object.
        if (ents.length > 0) {
            var text = obj.text;

            var html_l = 0
            var index_diff_l = 0

            for (e=0; e<ents.length; e++){
                // Get indices, account for moving
                var index0 = ents[e].indices[0] + html_l - index_diff_l;
                var index1 = index0 + ents[e].index_diff;

                var html = ents[e].html;
                var first_str = text.substring(0, index0);
                var last_str = text.substring(index1, text.length);
                text = first_str + html + last_str;

                html_l = html.length;
                index_diff_l = ents[e].index_diff;
            };
        } else {
            var text = obj.text;
        };

        var styles = [];
        styles.push('background-color: #' + obj.user.profile_background_color);
        if (obj.user.profile_use_background_image) {
            styles.push('background-image: url(' + obj.user.profile_background_image_url + ')');
            if (!obj.user.profile_background_tile) {
                styles.push('background-repeat: no-repeat');
            }
        }

        html_tmpl = '<div style="' + styles.join(';') + '" class="tweet right-tweet">'+
            '<p class="tweet-box">'+
                '<span class="tweet-author">'+
                    '<a class="tweet-av" href="http://www.twitter.com/'+ obj.user.screen_name +'/"><img height="48" width="48" src="'+ obj.user.profile_image_url +'"></a>'+
                    '<span class="tweet-name"><a class="tweet-screenname" href="http://www.twitter.com/'+ obj.user.screen_name +'/">@'+obj.user.screen_name+'</a><br><span class="tweet-full-name">'+ obj.user.name +'</span></span>'+
                '</span>'+
                '<span class="tweet-text">'+ text +'</span>'+
                '<span class="tweet-meta"><a href="http://www.twitter.com/'+ obj.user.screen_name +'/status/'+ obj.id_str +'">'+ obj.created_at.substr(3, 7) +', ' + obj.created_at.substr(26, 30)+'</a></span>'+
            '</p>'+
        '</div>';

        tweet_html.push(html_tmpl);
    };
    
    $('.tweet.throbber').replaceWith(tweet_html.join(''));
});
