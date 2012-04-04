(function() {
    CodeMirror.simpleHint = function(editor, getHints) {
        // We want a single cursor position.
        if (editor.somethingSelected()) return;
        var result = getHints(editor);
        if (!result || !result.list.length) return;
        var completions = result.list;
        function insert(str, token) {
            // if we're auto-completing a CSS property (not a selector or nested selector), append ': '
            if (token && token.className == 'css-identifier') {
                var properties = [].concat(suffixes, attrs);
                if (_.any(properties, function (x) { return str.indexOf(x) > -1; })) {
                    str += ': ';
                }
            }
            editor.replaceRange(str, result.from, result.to);
        }
        // When there is only one completion, use it directly.
        if (completions.length == 1) {insert(completions[0], result.token); return true;}

        // Build the select widget
        var complete = document.createElement("div");
        complete.className = "CodeMirror-completions";
        var sel = complete.appendChild(document.createElement("select"));
        // Opera doesn't move the selection when pressing up/down in a
        // multi-select, but it does properly support the size property on
        // single-selects, so no multi-select is necessary.
        if (!window.opera) sel.multiple = true;
        for (var i = 0; i < completions.length; ++i) {
            var opt = sel.appendChild(document.createElement("option"));
            opt.appendChild(document.createTextNode(completions[i]));
        }
        sel.firstChild.selected = true;
        sel.size = Math.min(10, completions.length);
        var pos = editor.cursorCoords();
        complete.style.left = pos.x + "px";
        complete.style.top = pos.yBot + "px";
        complete.style.position = 'absolute';
        complete.style.zIndex = 10001;
        document.body.appendChild(complete);
        // Hack to hide the scrollbar.
        if (completions.length <= 10)
            complete.style.width = (sel.clientWidth - 1) + "px";

        var done = false;
        function close() {
            if (done) return;
            done = true;
            complete.parentNode.removeChild(complete);
        }
        function pick() {
            insert(completions[sel.selectedIndex], result.token);
            close();
            setTimeout(function(){editor.focus();}, 50);
        }
        CodeMirror.connect(sel, "blur", close);
        CodeMirror.connect(sel, "keydown", function(event) {
            var code = event.keyCode;
            // Enter or Tab
            if (code == 13 || code == 9) {CodeMirror.e_stop(event); pick();}
            // Escape
            else if (code == 27) {CodeMirror.e_stop(event); close(); editor.focus();}
            else if (code != 38 && code != 40) {
                close(); editor.focus();
                setTimeout(function(){CodeMirror.simpleHint(editor, getHints);}, 50);
            }
        });
        CodeMirror.connect(sel, "dblclick", pick);

        sel.focus();
        // Opera sometimes ignores focusing a freshly created node
        if (window.opera) setTimeout(function(){if (!done) sel.focus();}, 100);
        return true;
    };
    var prefixes = [
            "-webkit-", "-moz-", "-o-", "-ms-", "-svg-", "-pie-", "-khtml-"
        ], suffixes = [
            "appearance", "background-clip", "background-inline-policy",
            "background-origin", "background-size", "binding", "border-bottom-colors",
            "border-left-colors", "border-right-colors", "border-top-colors",
            "border-end", "border-end-color", "border-end-style", "border-end-width",
            "border-image", "border-start", "border-start-color", "border-start-style",
            "border-start-width", "box-align", "box-direction", "box-flex",
            "box-flexgroup", "box-ordinal-group", "box-orient", "box-pack",
            "box-sizing", "column-count", "column-gap", "column-width", "column-rule",
            "column-rule-width", "column-rule-style", "column-rule-color", "float-edge",
            "font-feature-settings", "font-language-override",
            "force-broken-image-icon", "image-region", "margin-end", "margin-start",
            "opacity", "outline", "outline-color", "outline-offset", "outline-radius",
            "outline-radius-bottomleft", "outline-radius-bottomright",
            "outline-radius-topleft", "outline-radius-topright", "outline-style",
            "outline-width", "padding-end", "padding-start", "stack-sizing", "tab-size",
            "text-blink", "text-decoration-color", "text-decoration-line",
            "text-decoration-style", "transform", "transform-origin", "transition",
            "transition-delay", "transition-duration", "transition-property",
            "transition-timing-function", "user-focus", "user-input", "user-modify",
            "user-select", "window-shadow", "border-radius"
        ], attrs = [
            "azimuth", "background-attachment", "background-color",
            "background-image", "background-position", "background-repeat",
            "background", "border-bottom-color", "border-bottom-style",
            "border-bottom-width", "border-bottom", "border-collapse", "border-color",
            "border-left-color", "border-left-style", "border-left-width",
            "border-left", "border-right-color", "border-right-style",
            "border-right-width", "border-right", "border-spacing", "border-style",
            "border-top-color", "border-top-style", "border-top-width", "border-top",
            "border-width", "border", "bottom", "box-sizing", "caption-side", "clear",
            "clip", "color", "content", "counter-increment", "counter-reset",
            "cue-after", "cue-before", "cue", "cursor", "direction", "display",
            "elevation", "empty-cells", "float", "font-family", "font-size-adjust",
            "font-size", "font-stretch", "font-style", "font-variant", "font-weight",
            "font", "height", "left", "letter-spacing", "line-height",
            "list-style-image", "list-style-position", "list-style-type", "list-style",
            "margin-bottom", "margin-left", "margin-right", "margin-top",
            "marker-offset", "margin", "marks", "max-height", "max-width", "min-height",
            "min-width", "opacity", "orphans", "outline-color", "outline-style",
            "outline-width", "outline", "overflow", "overflow-x", "overflow-y",
            "padding-bottom", "padding-left", "padding-right", "padding-top", "padding",
            "page-break-after", "page-break-before", "page-break-inside", "page",
            "pause-after", "pause-before", "pause", "pitch-range", "pitch",
            "play-during", "position", "quotes", "richness", "right", "size",
            "speak-header", "speak-numeral", "speak-punctuation", "speech-rate",
            "speak", "stress", "table-layout", "text-align", "text-decoration",
            "text-indent", "text-shadow", "text-transform", "top", "unicode-bidi",
            "vertical-align", "visibility", "voice-family", "volume", "white-space",
            "widows", "width", "word-spacing", "z-index"
        ], functions = [
            "hsl", "hsla", "rgb", "rgba", "url", "attr", "counter", "counters",
            "abs", "adjust_color", "adjust_hue", "alpha", "join", "blue", "ceil",
            "change_color", "comparable", "complement", "darken", "desaturate", "floor",
            "grayscale", "green", "hue", "if", "invert", "join", "length", "lighten",
            "lightness", "mix", "nth", "opacify", "opacity", "percentage", "quote",
            "red", "round", "saturate", "saturation", "scale_color", "transparentize",
            "type_of", "unit", "unitless", "unqoute"
        ], values = [
            "absolute", "all-scroll", "always", "armenian", "auto", "baseline",
            "below", "bidi-override", "block", "bold", "bolder", "border-box", "both",
            "bottom", "break-all", "break-word", "capitalize", "center", "char",
            "circle", "cjk-ideographic", "col-resize", "collapse", "content-box",
            "crosshair", "dashed", "decimal-leading-zero", "decimal", "default",
            "disabled", "disc", "distribute-all-lines", "distribute-letter",
            "distribute-space", "distribute", "dotted", "double", "e-resize",
            "ellipsis", "fixed", "georgian", "groove", "hand", "hebrew", "help",
            "hidden", "hiragana-iroha", "hiragana", "horizontal", "ideograph-alpha",
            "ideograph-numeric", "ideograph-parenthesis", "ideograph-space", "inactive",
            "inherit", "inline-block", "inline", "inset", "inside", "inter-ideograph",
            "inter-word", "italic", "justify", "katakana-iroha", "katakana", "keep-all",
            "left", "lighter", "line-edge", "line-through", "line", "list-item",
            "loose", "lower-alpha", "lower-greek", "lower-latin", "lower-roman",
            "lowercase", "lr-tb", "ltr", "medium", "middle", "move", "n-resize",
            "ne-resize", "newspaper", "no-drop", "no-repeat", "nw-resize", "none",
            "normal", "not-allowed", "nowrap", "oblique", "outset", "outside",
            "overline", "pointer", "progress", "relative", "repeat-x", "repeat-y",
            "repeat", "right", "ridge", "row-resize", "rtl", "s-resize", "scroll",
            "se-resize", "separate", "small-caps", "solid", "square", "static",
            "strict", "super", "sw-resize", "table-footer-group", "table-header-group",
            "tb-rl", "text-bottom", "text-top", "text", "thick", "thin", "top",
            "transparent", "underline", "upper-alpha", "upper-latin", "upper-roman",
            "uppercase", "vertical-ideographic", "vertical-text", "visible", "w-resize",
            "wait", "whitespace", "zero"
        ], colors = [
            "aqua", "black", "blue", "fuchsia", "gray", "green", "lime", "maroon", "navy",
            "olive", "orange", "purple", "red", "silver", "teal", "white", "yellow"
        ], ats = [
            "@mixin", "@extend", "@include", "@import", "@media", "@debug", "@warn",
            "@if", "@for", "@each", "@while", "@else", "@font-face", "@-webkit-keyframes"
        ], selectors = [
            "a", "abbr", "acronym", "address", "applet", "area", "article", "aside",
            "audio", "b", "base", "basefont", "bdo", "big", "blockquote", "body", "br",
            "button", "canvas", "caption", "center", "cite", "code", "col", "colgroup",
            "command", "datalist", "dd", "del", "details", "dfn", "dir", "div", "dl",
            "dt", "em", "embed", "fieldset", "figcaption", "figure", "font", "footer",
            "form", "frame", "frameset", "h1", "h2", "h3", "h4", "h5", "h6", "head",
            "header", "hgroup", "hr", "html", "i", "iframe", "img", "input", "ins",
            "keygen", "kbd", "label", "legend", "li", "link", "map", "mark", "menu",
            "meta", "meter", "nav", "noframes", "noscript", "object", "ol", "optgroup",
            "option", "output", "p", "param", "pre", "progress", "q", "rp", "rt",
            "ruby", "s", "samp", "script", "section", "select", "small", "source",
            "span", "strike", "strong", "style", "sub", "summary", "sup", "table",
            "tbody", "td", "textarea", "tfoot", "th", "thead", "time", "title", "tr",
            "tt", "u", "ul", "var", "video", "wbr", "xmp"
        ], units = [
            "px", "em", "pt", "%"
        ];
    function getCompletions(token) {
        var completions = [];
        if (token.className == 'css-selector') {
            completions = completions.concat(selectors);
        }
        else if (token.className == 'css-identifier') {
            if (token.string.indexOf('-') == 0) {
                if (_.any(prefixes, function (x) { return token.string.indexOf(x) == 0; })) {
                    // We have a full custom browser attribute already specified.
                    completions = completions.concat(
                            _.flatten(
                                _.map(prefixes,
                                    function (x) { 
                                        if (token.string.indexOf(x) == 0) return _.map(suffixes, function(y) { return x + y; });
                                        else return [];
                                    })));
                }
                else {
                    completions = completions.concat(prefixes);
                }
            }
            else {
                completions = completions.concat(selectors, attrs);
            }
        }
        else if (token.className == 'css-at') {
            completions = completions.concat(ats);
        }
        else if (token.className == 'css-value') {
            completions = completions.concat(values, colors, _.map(functions, function(x) { return x + '('; }));
        }
        else if (token.className == 'css-unit') {
            var m = token.string.match(/^(-?\d*)(\D*)$/),
                num = m[1],
                unit = m[2];
            completions = completions.concat(_.flatten(_.map(units, function (x) { if (x.indexOf(unit) == 0) return num + x; else return []; })));
        }
        completions = _.filter(completions, function (x) { return x.indexOf(token.string) == 0; });
        return completions.sort();
    };
    CodeMirror.scssHints = function(editor) {
        var cur = editor.getCursor(), token = editor.getTokenAt(cur);
        return {
            list: getCompletions(token),
            from: {line: cur.line, ch: token.start},
            to: {line: cur.line, ch: token.end},
            token: token
        };
    };
})();
