function indexOfAny(s, chs, start) {
    var minFind = s.length + 1;
    var fFind = false;
    for (var i in chs) {
        var find = s.indexOf(chs[i], start);
        if (find !== -1) {
            minFind = Math.min(minFind, find);
            fFind = true;
        }
    }
    if (!fFind) return -1;
    return minFind;
}

function getSelectors(s, cursor) {
    var line = cursor.line;
    var col = cursor.ch;
    // Get just the first r lines and c characters.
    var rg = s.split('\n');
    rg.splice(line+1, rg.length - (line+1));
    rg[rg.length-1] = rg[rg.length-1].substring(0, col);
    var sToCursor = rg.join('\n');
    var cToCursor = sToCursor.length;
    var sFromCursor = s.substring(cToCursor);
    var firstEnd = indexOfAny(sFromCursor, [';', ')', '}']);
    var nextStart = sFromCursor.indexOf('{');

    // Make sure we're in a selector.
    if (nextStart === -1 || (firstEnd !== -1 && nextStart > firstEnd)) return null;
    // Don't match the whitespace before a selector.
    if (sToCursor.match(/[;){}]\s*$/) && sFromCursor.match(/^\s/)) return null;

    nextStart += cToCursor;
    s = s.substring(0, nextStart);
    // Remove multi-line comments.
    s = s.replace(/\/\*(.|\r|\n)*?\*\//gi, '');
    // Remove single-line comments, @import statements, and @media queries
    s = s.replace(/^\s*(\/\/|@import|@media).*$/gmi, '');
    // Make sure there are spaces around curlies and commas.
    s = s.replace(/\s*([{},])\s*/gi, ' $1 ');
    // Replace all whitespace with a single space.
    s = $.trim(s.replace(/\s+/gi, ' '));
    rg = s.split(' ');

    // We should always start out in a selector.
    var fInSelector = true;
    var c = 0;
    var selectors = [];
    var curSelector = [];
    for (var i = rg.length-1; i >= 0; i--) {
        if (fInSelector) {
            curSelector.unshift(rg[i]);
            if (i === 0 || rg[i-1].match(/[;{})]$/gi)) {
                selectors.unshift(curSelector.join(' '));
                curSelector = [];
                fInSelector = false;
            }
        }
        else if (rg[i] === '}') c++;
        else if (rg[i] === '{') {
            if (c > 0) c--;
            else fInSelector = true;
        }
    }

    if (selectors.length === 1) {
        if (selectors[0] === 'body' || selectors[0] === 'html') {
            // Showing the whole body or html, especially if it's been styled,
            // isn't very useful. Don't highlight.
            return null;
        }
    }

    return selectors;
}

function highlightSelectors(E) {
    var editor = E.editor;
    var cursor = editor.getCursor();
    if (editor.somethingSelected() || (cursor.line === 0 && cursor.ch === 0)) {
        removeHighlights(E);
        return;
    }
    var selectors = getSelectors(editor.getValue(), cursor);
    E.comm.sendMessage('editor', 'highlight', {selectors: selectors}, E.iframe.contentWindow);
}

function removeHighlights(E) {
    E.comm.sendMessage('editor', 'highlight', {selectors: null}, E.iframe.contentWindow);
}
