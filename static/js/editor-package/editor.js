;(function(window, document, undefined) {
    var editorTop = $('#editor-wrapper').position().top;
    var timesince = function (dt) {
        var past_ = "ago";
        var future_ = "from now";
        var def = "just now";

        var now = new Date();
        var diff, dt_is_past;

        if(!_.isDate(dt)) {
            dt = new Date(dt);
        }

        if (now > dt) {
            diff = (now - dt) / 1000;
            dt_is_past = true;
        } else {
            diff = (dt - now) / 1000;
            dt_is_past = false;
        }

        var seconds_in_a = {
            year: 31556926,
            month: 2629744,
            day: 86400,
            hour: 3600,
            minute: 60
        };

        var periods = [
            [diff / seconds_in_a.year, "year", "years"],
            [diff / seconds_in_a.month, "month", "months"],
            [diff / seconds_in_a.week, "week", "weeks"],
            [diff / seconds_in_a.day, "day", "days"],
            [diff / seconds_in_a.hour, "hour", "hours"],
            [diff / seconds_in_a.minute, "minute", "minutes"],
            [diff, "second", "seconds"]
        ];

        for (var ix = 0; ix < periods.length; ix++) {
            var period = Math.floor(periods[ix][0]);
            var singular = periods[ix][1];
            var plural = periods[ix][2];
            if (period > 0) {
                return period + ' ' + (period === 1 ? singular : plural) + ' ' + (dt_is_past ? past_ : future_);
            }
        }
        return def;
    };

    var showMsg = function(sMsg, style, fFadeOut){
        var msg = $('#msg');
        msg
        .text(sMsg)
        .attr('class', style)
        .fadeTo('slow', 1);

        if(fFadeOut){
            setTimeout(function(){
                msg.fadeTo('slow', 0);
            }, 3000);
        }
    };


    var autoSave = _.debounce(function(styleId, newScss) {
        channelSend({
            cmd: 'save',
            'style_id': styleId,
            'page_key': Editor.pageKey,
            'scss': newScss
        }, function(data) {
            //Editor.blinkMsg('Saved!');
            Logger.log('editor', ['autosave', data]);
            Editor.preview_css = data['css'];
            if (data['log']) {
                $('#btn-scss-warning').fadeIn();
                $('#scss-warning-log').html(data['log']);
                if ($('#editor-wrapper').position().top != editorTop) {
                    _.delay(function() {
                        $('#editor-wrapper').animate({top: editorTop + $('#scss-warning-log').outerHeight()});
                    }, 250);
                }
            }
            else {
                $('#btn-scss-warning').fadeOut();
                $('#editor-wrapper').animate({top: editorTop}, function() {
                    $('#scss-warning-log').html('');
                });
            }
            Editor.currentStyle().preview_dt_last_edit = new Date();
            Editor.sendMessage(Editor.preview_css);
            if (Editor.previewMode) {
                updateLastEdited(Editor.currentStyle().preview_dt_last_edit);
            }
        });
    }, 500);

    /* Channel API handlers */

    var channelOpen = function() {
        Logger.log('channels', ['editor', 'socket opened']);
        channelSend({cmd: 'open'});
    };

    var channelReceive = function(message) {
        var data = message.data;
        if (_.isString(data)) data = JSON.parse(data);
        if (!data || !data.cmd) return;
        Logger.log('channels', ['editor', 'incoming message', message]);
        $('#edit-pane').removeClass('loading'); // once we've recieved a message, we're done "loading"
        switch (data.cmd) {
            case 'lock':
                var name;
                var email;
                if(data.user && data.user.name && data.user.email) {
                    name = data.user.name;
                    email = data.user.email;
                }
                lockEditor(name, email);
                break;
            case 'unlock':
                unlockEditor();
                break;
        }
    };

    var channelError = function(err) {
        Logger.log('channels', ['editor', 'channel error', err]);
    };

    var channelClose = function() {
        Editor.channel = null;
        Editor.socket = null;
        Editor.channelToken = null;
        Logger.log('channels', ['editor', 'channel closed']);
    };

    var channelSend = function(data, callback) {
        message = JSON.stringify({from: Editor.channelToken, data: data});
        Logger.log('channels', ['editor', 'outgoing message', message]);
        $.ajax(Urls['page_rpc'], {
            type: 'POST',
            data: {message: message},
            dataType: 'json',
            success: function(data, status, jxhr) { 
                if (data.cmd === 'refresh') showRefreshMessage();
                else if (_.isFunction(callback)) callback(data, status, jxhr);
            },
            error: showRefreshMessage
        });

    };

    /* End Channel API Handlers */

    var lockEditor = function(name, email) {
        Editor.locked = true;
        if(name && email) {
            $('#lock-msg').text('Locked by ' + name + '. ').attr('class', 'locked');
        } else {
            $('#lock-msg').text('Locked by another user. ').attr('class', 'locked');
        }
        var unlock = $('<a>')
            .attr({href: '#'})
            .text('Claim lock...')
            .click(claimLock)
            .appendTo('#lock-msg');
        $('#edit-pane').addClass('locked');
        disableEditor();
    };

    var doUnlock = function(styles) {
        $('#edit-pane').removeClass('loading');
        if (styles) {
            Editor.styles = styles;
            var scss = Editor.previewMode ? Editor.currentPreviewScss() : Editor.currentPublishedScss();
            var dtLastEdit = Editor.previewMode ? Editor.currentStyle().preview_dt_last_edit : Editor.currentStyle().published_dt_last_edit;
            updateLastEdited(dtLastEdit);
            Editor.fSwitching = true; // don't trigger an autosave
            Editor.editor.setValue(scss);
            Editor.editor.clearHistory();
        }
        Editor.locked = false;
        $('#lock-msg').text('Unlocked!').attr('class', 'unlocked');
        $('#edit-pane').removeClass('locked');
        if (Editor.previewMode && !($('body').hasClass('missing-tags'))) {
            enableEditor();
        }
    };

    var unlockEditor = function() {
        if (Editor.locked) {
            $('#edit-pane').removeClass('locked').addClass('loading');
            $.getJSON(Urls['page_styles'], doUnlock);
        }
        else {
            doUnlock();
        }
    };

    var showRefreshMessage = function() {
        lockEditor();
        $('#lock-msg').text('You have lost connection to the server. Please refresh the page and try again.');
    };

    var claimLock = function() {
        if (confirm('Another user may be editing this page right now.\nAre you sure you want to override the lock?')) {
            channelSend({cmd: 'claimLock'});
        }
        return false;
    };

    var disableEditor = function(fShowLoading) {
        Editor.editor.setOption('readOnly', true);
        $('#btn-publish').attr({disabled: 'disabled'});
        $('#edit-pane').addClass('disabled');
        if (fShowLoading) {
            $('#edit-pane').addClass('loading');
        }
    };

    var enableEditor = function() {
        Editor.editor.setOption('readOnly', false);
        $('#btn-publish').removeAttr('disabled');
        $('#edit-pane').removeClass('disabled').removeClass('loading');
    };

    var switchMode = function(showPreview) {
        if(showPreview === Editor.previewMode) return; // nothing to do
        Editor.saveEditorState();
        Editor.fSwitching = true;
        Editor.previewMode = showPreview;
        var scss = showPreview ? Editor.currentPreviewScss() : Editor.currentPublishedScss();
        var css = showPreview ? Editor.preview_css : Editor.published_css;
        Editor.editor.setValue(scss);
        Editor.restoreEditorState();
        Editor.sendMessage(css);

        var dtLastEdit = showPreview ? Editor.currentStyle().preview_dt_last_edit : Editor.currentStyle().published_dt_last_edit;
        updateLastEdited(dtLastEdit);

        var canEdit = showPreview && !Editor.locked && !($('body').hasClass('missing-tags'));
        if(canEdit) {
            enableEditor();
        } else {
            disableEditor();
        }

        if (!showPreview) {
            $('#edit-pane').addClass('published');
            $('#btn-export').attr('href', Urls['page_export_css']);
        } else {
            $('#edit-pane').removeClass('published');
            $('#btn-export').attr('href', Urls['page_export_css'] + '&preview');
        }

        Editor.editor.focus();
    };

    var updatePageLink = function(href, fMissingTags, fUnknownUrl) {
        var $select = $('select.page-link');
        var existingUrls = _.pluck($select.find('option'), 'value');

        if (fUnknownUrl) {
            href = '<unknown url>';
        } else {
            existingUrls = _.without(existingUrls, '<unknown url>');
            $select.find('option[value="<unknown url>"]').remove();
        }

        // only change the droplist's content/selection if href is defined.
        // href === null means the url is known, but missing tags
        if (href) {
            var foundIx = _.indexOf(existingUrls, href);
            if (foundIx < 0) {
                $select.append(new Option(href, href));
            }
            $select.val(href);
        }

        if (fMissingTags) {
            disableEditor();
            $('body').addClass('missing-tags');
            // can't refresh unknown urls, so make the refresh button look
            // like it's disabled (clicking it is a no-op in missing-tags mode)
            if (fUnknownUrl) {
                $('body').addClass('unknown-url');
            }
        } else {
            if (Editor.previewMode && !Editor.locked) {
                enableEditor();
            }
            $('body').removeClass('missing-tags unknown-url');
        }
    };

    var getPageUrl = function() {
        var newUrl = $('select.page-link').val();
        if (newUrl !== '<unknown url>') {
            return newUrl;
        }
        return null;
    };

    var updateLastEdited = function(dt) {
        $('#style-dt-last-edit').text(timesince(dt));
    };

    var Editor = window.Editor = {

        channelToken: null,
        channel: null,
        socket: null,
        styles: [],
        ixCurrentStyle: -1,
        previewMode: true,
        locked: false,
        pageKey: null,
        editor: null,
        fSwitching: false,
        comm: null,
        iframe: null,

        currentPreviewScss: function() {
            if (Editor.ixCurrentStyle < 0) return '';
            return Editor.styles[Editor.ixCurrentStyle].preview_scss;
        },

        currentPublishedScss: function() {
            if (Editor.ixCurrentStyle < 0) return '';
            return Editor.styles[Editor.ixCurrentStyle].published_scss;
        },

        currentStyle: function() {
            if (Editor.ixCurrentStyle < 0) return null;
            return Editor.styles[Editor.ixCurrentStyle];
        },

        saveEditorState: function() {
            if(Editor.ixCurrentStyle < 0) return;
            var sPrefix = Editor.previewMode ? 'preview' : 'published';
            var sStart = sPrefix + '_cursor_start';
            var sEnd = sPrefix + '_cursor_end';
            var sHistory = sPrefix + '_history';
            Editor.currentStyle()[sStart] = Editor.editor.getCursor(true);
            Editor.currentStyle()[sEnd] = Editor.editor.getCursor(false);
            Editor.currentStyle()[sHistory] = Editor.editor.getHistory();
            Editor.editor.clearHistory(); // avoid polluting current history object with any upcoming events
        },

        restoreEditorState: function() {
            if(Editor.ixCurrentStyle < 0) return;
            var sPrefix = Editor.previewMode ? 'preview' : 'published';
            var sStart = sPrefix + '_cursor_start';
            var sEnd = sPrefix + '_cursor_end';
            var sHistory = sPrefix + '_history';
            var start = Editor.currentStyle()[sStart];
            var end = Editor.currentStyle()[sEnd];
            var hist = Editor.currentStyle()[sHistory];
            if (start && end) {
                Editor.editor.setSelection(start, end);
            }
            if (hist) {
                Editor.editor.setHistory(hist);
            } else {
                // if we don't have a history object to restore, clear the history so
                // that upcoming events don't pollute the existing history object
                Editor.editor.clearHistory();
            }
        },

        updateCurrentStyle: function(newScss) {
            if(Editor.ixCurrentStyle < 0) return;
            if(Editor.previewMode && !Editor.fSwitching){
                Editor.currentStyle().preview_scss = newScss;
                autoSave(Editor.currentStyle().id, newScss);
            }
        },

        publishCurrentStyle: function(newScss) {
            if(Editor.ixCurrentStyle < 0) return;
            Editor.showThrobber('Saving...');
            style = Editor.currentStyle();
            style.published_scss = style.preview_scss = newScss;
            style.published_cursor_start = style.preview_cursor_start;
            style.published_cursor_end = style.preview_cursor_end;
            channelSend({
                cmd: 'save',
                'style_id': Editor.currentStyle().id,
                'page_key': Editor.pageKey,
                'scss': newScss,
                fPublish: true
            }, function(data){
                Editor.blinkMsg('Published!');
                Editor.preview_css = Editor.published_css = data;
                Editor.currentStyle().published_dt_last_edit = new Date();
                if (!Editor.previewMode) {
                    updateLastEdited(Editor.currentStyle().published_dt_last_edit);
                }
            });
        },

        previewFrameReady: false,
        previewFrameInitialLoad: true,
        previewFrameLoaded: function() {
            setTimeout(function() {
                Logger.log('editor', ['preview frame loaded', 'ET phoned home?', Editor.previewFrameReady]);
                if (!Editor.previewFrameReady) {
                    updatePageLink(null, true, !Editor.previewFrameInitialLoad);
                }
                Editor.previewFrameReady = false; // reset the flag to accommodate iframe navigation
                Editor.previewFrameInitialLoad = false;
            }, 500);
        },

        navigatePreviewPane: function(url) {
            updatePageLink(url, false, false);
            disableEditor(true);
            Editor.previewFrameInitialLoad = true; // this is effectively the same as refreshing the page, so make sure things behaves that way
            Editor.iframe.src = url;
        },

        updatePageDetails: function(name, url, preview_urls) {
            // update page name
            document.title = name + document.title.substr(document.title.lastIndexOf(' - '));
            $('#page-name').text(name);

            // rebuild the list of preview urls
            var $select = $('select.page-link');
            $('option', $select).remove();
            $select.append(new Option(url, url));
            $.each(preview_urls, function(ix, el) {
                $select.append(new Option($(el).val(), $(el).val()));
            });
            $select.val(url); // select & navigate to the main preview url

            // update page url
            Editor.navigatePreviewPane(url);
        },

        sendMessage: function(message, command) {
            command = command || 'update';
            Editor.comm.sendMessage('editor', command, message, Editor.iframe.contentWindow);
        },

        blinkMsg: function(sMsg){
            showMsg(sMsg, 'success', true);
        },

        showThrobber: function(sMsg){
            showMsg(sMsg, 'throbber', false);
        },

        errorMarkings: [],

        clearErrors: function() {
            $('pre[aria-describedby]').attr('aria-describedby', null);
            _.each(Editor.errorMarkings, function(f) { f.clear(); });
            Editor.errorMarkings = [];
        },

        checkErrors: function() {
            var editor = Editor.editor;
            if (!editor) return;

            var reUrl = /url\s*\(\s*['"]?(.*?)['"]?\s*\)/
            var reHttp = /^(data:|(https?:)?\/\/)/

            Editor.clearErrors();
            _.each(_.range(editor.lineCount()), function(i) {
                var s = editor.getLine(i);
                var m = null;
                if ((m = s.match(reUrl))) {
                    var url = m[1];
                    if (!url.match(reHttp)) {
                        var start = s.indexOf(url);
                        var end = start + url.length;
                        Editor.errorMarkings.push(
                            editor.markText({line: i, ch: start}, {line: i, ch: end}, 'error relative-url')
                        );

                    }
                }
            });

            setTimeout(function() {
                /* Create a tooltip about relative URLs, to show if we find any. */
                $('.CodeMirror').qtip({
                    content: {text: 'ERROR: You cannot use relative URLs in WebPutty'},
                    show: { target: $('.relative-url') },
                    hide: { target: $('.relative-url'), leave: false },
                    position: { target: 'mouse', at: 'bottom left', adjust: { x: 10, y: 10} },
                    style: { classes: 'ui-tooltip-red ui-tooltip-rounded' }
                });
            }, 100);
        },

        previewFrameLog: function(region) {
            region = region || 'all';
            Editor.sendMessage(region, 'printLog');
        },

        init: function() {
            Editor.channel = new goog.appengine.Channel(Editor.channelToken);
            Editor.socket = Editor.channel.open({
                onopen: channelOpen,
                onmessage: channelReceive,
                onerror: channelError,
                onclose: channelClose
            });
            Editor.socket.onopen = channelOpen;
            Editor.socket.onmessage = channelReceive;
            Editor.iframe = $('#preview-iframe')[0];

            if(Editor.ixCurrentStyle < 0) {
                Logger.log('editor', ['invalid ixCurrentStyle', Editor.ixCurrentStyle, 'WTF, mate?']);
            }

            var activeLine = null;
            var editor = Editor.editor = CodeMirror(
                function(newEditor) {
                    $('#css-loader').replaceWith(newEditor);
                }, {
                value: Editor.currentPreviewScss(),
                readOnly: true,
                indentUnit: 2,
                lineNumbers: true,
                lineWrapping: true,
                matchBrackets: true,
                tabMode: 'shift',
                extraKeys: {"Ctrl-Space": function(ed) {CodeMirror.simpleHint(ed, CodeMirror.scssHints);}},
                onChange: function(self) {
                    Editor.updateCurrentStyle(self.getValue());
                    Editor.fSwitching = false;
                    Editor.checkErrors();
                },
                onCursorActivity: _.throttle(function() {
                    highlightSelectors(Editor);
                    if (activeLine) {
                        editor.setLineClass(activeLine, null); // clear previous active line
                    }
                    activeLine = editor.setLineClass(editor.getCursor().line, "activeLine");
                }, 250)
            });

            $(window).resize(_.throttle(function() {
                removeHighlights(Editor);
                resizePreviewUrls();
            }, 100));
            $(window).resize(_.debounce(function() {
                highlightSelectors(Editor);
            }, 250));

            var fWarnedMissingStyle = false;
            Editor.comm.receiveMessage('editor', function(){return true;}, {
                ready: function(data) {
                    Editor.previewFrameReady = true;
                    updatePageLink(data.href, false, false);
                    Editor.sendMessage(Editor.previewMode ? Editor.preview_css : Editor.published_css);
                },
                missing_style_tag: function(data) {
                    if (!fWarnedMissingStyle) {
                        fWarnedMissingStyle = true;
                        updatePageLink(data.href, true, false);
                        var $dlg = $('#dlg-missingtags');
                        $dlg.modal({
                            overlayId: 'embed-overlay',
                            overlayCss: {background: '#000', opacity: 0.7},
                            overlayClose: true
                        });
                    }
                }
            });
            Editor.comm.sendMessage('editor', 'ready', {}, Editor.iframe.contentWindow);
            $('#preview-iframe').load(Editor.previewFrameLoaded);
            // we set window.previewFrameLoaded directly via the iframe's onload attribute
            // to cover the case where the iframe loads before document ready fires
            if (window.previewFrameLoaded) Editor.previewFrameLoaded();

            $('#btn-publish').click(function(){
                if ($('#version-controls select').val() === 'published') return;
                Editor.publishCurrentStyle(editor.getValue());
            });

            var fFocusing = false;
            $('textarea.embed')
            .focus(function(e) {
                fFocusing = true;
                $(this).select();
            })
            .mouseup(function(e){
                if(fFocusing){
                    fFocusing = false;
                    // work around webkit bug https://bugs.webkit.org/show_bug.cgi?id=22691
                    if(e.preventDefault) e.preventDefault();
                }
            });

            $('#btn-embed, #btn-fix-it').click(function(){
                $dlg = $('#embed-dlg');
                $dlg.modal({
                    overlayId: 'embed-overlay',
                    overlayCss: {background: '#000', opacity: 0.7},
                    overlayClose: true
                });
                $dlg.find('textarea').focus();
                return false;
            });

            $('#btn-missing-tags-override').click(function() {
                if (confirm('The live preview pane will not work, but you will be able to edit and publish your stylesheet\'s SCSS.\n\nAre you sure you want to proceed?')){
                    $('body').removeClass('missing-tags');
                    if(Editor.previewMode && !Editor.locked) {
                        enableEditor();
                    }
                }
                return false;
            });

            $('#btn-refresh').click(function() {
                var newUrl = getPageUrl();
                if (newUrl) {
                    // only try to refresh if it's a known url
                    Editor.navigatePreviewPane(newUrl);
                }
                return false;
            });

            $('#btn-open-url').click(function() {
                var newUrl = getPageUrl();
                if (newUrl) {
                    window.open(newUrl);
                }
            });

            $('#btn-add-firebug').click(function() {
                var newUrl = getPageUrl();
                if (newUrl && !$('body').hasClass('missing-tags')) {
                    Editor.sendMessage(true, 'firebug');
                }
                return false;
            });

            $('#btn-scss-warning').click(function() {
                if ($('#editor-wrapper').position().top != editorTop) {
                    $('#editor-wrapper').animate({top: editorTop});
                } else {
                    $('#editor-wrapper').animate(
                        {top: editorTop + $('#scss-warning-log').outerHeight()},
                        fixCodeMirror
                    );
                }
                return false;
            });

            $('select.page-link').change(function() {
                var newUrl = $(this).val();
                Editor.navigatePreviewPane(newUrl);
            });

            var loadLayout = function() {
                var layoutMode = $.Storage.get('layoutMode') || 'columns';
                var layoutSize = parseInt($.Storage.get('layoutSize') || 50);
                if (layoutMode !== 'columns') {
                    btnRowLayout.click();
                }
                updateLayout(layoutMode, layoutSize);
            };

            var updateLayout = function(layout, size) {
                if(layout === 'columns') {
                    $('#content .left').css('width', size + '%');
                    $('#content .right').css('width', (100 - size) + '%');
                    $('#content #drag-handle').css('left', size + '%');
                    resizePreviewUrls();
                } else {
                    $('#content .top').css('height', size + '%');
                    $('#content .bottom').css({height: (100 - size) + '%', top: size + '%'});
                    $('#content #drag-handle').css('top', size + '%');
                    fixCodeMirror();
                }
                $.Storage.set({
                    layoutMode: layout,
                    layoutSize: size
                });
            };

            var switchLayout = function(columns) {
                if ($('#edit-pane').hasClass('column') === columns) return; // nothing to do

                $('#btn-row-layout').toggleClass('selected');
                $('#btn-column-layout').toggleClass('selected');

                if (columns) {
                    $('#drag-handle').attr('style', '').removeClass('rows').addClass('columns');
                    $('#preview-pane').attr('style', '').removeClass('row top').addClass('column left');
                    $('#edit-pane').attr('style', '').removeClass('row bottom').addClass('column right');
                } else {
                    $('#drag-handle').attr('style', '').removeClass('columns').addClass('rows');
                    $('#preview-pane').attr('style', '').removeClass('column left').addClass('row top');
                    $('#edit-pane').attr('style', '').removeClass('column right').addClass('row bottom');
                }
                fixCodeMirror();
                resizePreviewUrls();
                updateLayout(columns ? 'columns' : 'rows', 50);
                highlightSelectors(Editor);
            };

            var fixCodeMirror = function() {
                $('.CodeMirror-gutter').height($('.CodeMirror').height()); // avoid scroll bars in the editor/gaps in its gutter
            };

            var resizePreviewUrls = function() {
                var buttons = $('.preview-nav-button');
                var newMaxWidth = $('#page-info').width() - $('#version-controls').width() - (12 + (buttons.width() * buttons.length));
                $('.page-link').css('max-width', newMaxWidth);
            };

            GhettoSplitter.makeSplitter(
                $('#drag-handle'),
                {
                    onDragStart: function(evt) {
                        $('body').css('cursor', this.hasClass('columns') ? 'col-resize' : 'row-resize');
                        $('#content .drag-shim').show();
                        removeHighlights(Editor);
                    },
                    onDrag: function(evt){
                        var minColWidth = 280; // pixels
                        var minRowHeight = 130; // pixels

                        if(this.hasClass('columns')){
                            // get X coordinate relative to #content
                            var relX = evt.pageX - $('#content').offset().left;

                            // bounds check to avoid overly-squished columns
                            var contentWidth = $('#content').width();
                            relX = Math.max(minColWidth, relX);
                            relX = Math.min(relX, contentWidth - minColWidth);

                            // calculate percentage width
                            var newWidth = relX / contentWidth * 100;

                            // update sizes & save the layout
                            updateLayout('columns', newWidth);
                        }else{
                            // get Y coordinate relative to #content
                            var relY = evt.pageY - $('#content').offset().top;

                            // bounds check to avoid overly-squished rows
                            var contentHeight = $('#content').height();
                            relY = Math.max(minRowHeight, relY);
                            relY = Math.min(relY, contentHeight - minRowHeight);

                            // calculate percentage height
                            var newHeight = relY / contentHeight * 100;

                            // update sizes & save the layout
                            updateLayout('rows', newHeight);
                        }
                    },
                    onDragStop: function(evt){
                        $('body').css('cursor', 'default');
                        $('#content .drag-shim').hide();
                        highlightSelectors(Editor);
                    }
                }
            );

            // switch to column layout
            var btnColumnLayout = $('#btn-column-layout').click(function(){
                switchLayout(true);
            });

            // switch to row layout
            var btnRowLayout = $('#btn-row-layout').click(function(){
                switchLayout(false);
            });

            loadLayout();

            $('#version-controls select').change(function(){
                switchMode($(this).val() === 'preview');
            });

            Editor.checkErrors();
        }
    }
})(window, document);
