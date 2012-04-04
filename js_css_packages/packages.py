javascript = {
    "shared": {
        "hashed-filename": "hashed-@shared@.js", # @content@ will be replaced with hash by deploy script
        "files": [
            "guiders-1.1.2.js",
            "jquery.simplemodal.1.4.1.min.js",
            "jquery.formalize.min.js",
            "jquery.tmpl.1.0.0pre.min.js",
            "underscore.1.1.7.min.js",
            "base.js",
        ]
    },
    "index": {
        "hashed-filename": "hashed-@index@.js", # @content@ will be replaced with hash by deploy script
        "files": [
            "index.js",
            "index_animations.js",
            "edit_siteusers.js",
        ]
    },
    "editor": {
        "hashed-filename": "hashed-@editor@.js", # @content@ will be replaced with hash by deploy script
        "files": [
            "jquery.Storage.min.js",
            "jquery.qtip.min.js",
            "../../codemirror/codemirror.js",
            "../../codemirror/css.js",
            "autocomplete.js",
            "ghetto_splitter.js",
            "highlighter.js",
            "editor.js",
            "edit_page.js",
        ]
    },
    "docs": {
        "hashed-filename": "hashed-@docs@.js", # @content@ will be replaced with hash by deploy script
        "files": [
            "prettify.js",
        ]
    },
    "stats": {
        "hashed-filename": "hashed-@stats@.js", # @content@ will be replaced with hash by deploy script
        "files": [
            "highcharts.js",
        ],
    },
}

stylesheets = {
    "shared": {
        "hashed-filename": "hashed-@shared@.css", # @content@ will be replaced with hash by deploy script
        "files": [
            "reset.css",
            "formalize.css",
            "main.css",
        ]
    },
    "editor": {
        "hashed-filename": "hashed-@editor@.css", # @content@ will be replaced with hash by deploy script
        "files": [
            "../../codemirror/codemirror.css",
            "../../codemirror/css.css",
            "jquery.qtip.min.css",
            "editor.css",
        ]
    },
    "docs": {
        "hashed-filename": "hashed-@docs@.css", # @content@ will be replaced with hash by deploy script
        "files": [
            "prettify.css",
        ]
    },
}
