# -*- coding: utf-8 -*-
"""
flaskext.markdown
~~~~~~~~~~~~~~~~~

Markdown filter class for Flask
To use::

    from flaskext.markdown import Markdown
    md = Markdown(app)

Then in your template::

    {% filter markdown %}
    Your Markdown
    =============
    {% endfilter %}

You can also do::

    {{ mymarkdown|markdown}}


Optionally, you can keep a reference to the Markdown instance and use that
to register custom extensions by calling :func:`register_extension` or
decorating the extension class with :func:`extend`

:copyright: (c) 2010 by Dan Colish.
:license: BSD, MIT see LICENSE for more details.
"""
from __future__ import absolute_import
from flask import Markup
import markdown as md
from markdown import (
    blockprocessors,
    Extension,
    preprocessors,
)


__all__ = ['blockprocessors', 'Extension', 'Markdown', 'preprocessors']


class Markdown(object):
    """
    Simple wrapper class for Markdown objects, any options that are available
    for markdown may be passed as keyword arguments like so::

      md = Markdown(app,
                    extensions=['footnotes'],
                    extension_configs={'footnotes': ('PLACE_MARKER','~~~~~~~~')},
                    safe_mode=True,
                    output_format='html4',
                   )

    You can then call :func:`register_extension` to load custom extensions into
    the Markdown instance or use the :func:`extend` decorator

    :param app: Your Flask app instance
    :param markdown_options: Keyword args for the Markdown instance
    """

    def __init__(self, app, **markdown_options):
        """Markdown uses old style classes"""
        self._instance = md.Markdown(**markdown_options)
        app.jinja_env.filters.setdefault('markdown', self)

    def __call__(self, stream):
        return Markup(self._instance.convert(stream))

    def extend(self, configs=None):
        """
        Decorator for registering macros

        You must either force the decorated class to be imported
        or define it in the same file you instantiate Markdown.
        To register a simple extension you could do::

          from flaskext.markdown import Extension, Markdown
          from preprocessors import SimplePreprocessor
          markdown_instance = Markdown(app)

          @markdown_instance.make_extension()
          class SimpleExtension(Extension):
               def extendMarkdown(self, md, md_globals):
               md.preprocessors.add('prover_block',
                                    SimplePreprocessor(md),
                                    '_begin')
               md.registerExtension(self)

        :param configs: A dictionary of options for the extension being registered
        """

        def decorator(ext_cls):
            return self.register_extension(ext_cls, configs)
        return decorator

    def register_extension(self, ext_cls, configs=None):
        """
        This will register an extension class with self._instance. You may pass
        any additional configs required for your extension

        It is best to call this when starting your Flask app, ie.::

          from .mdx_simpl import SimpleExtension

          md = Markdown(app)
          md.register_extension(SimpleExtension)

        Any additional configuration arguments can be added to configs and will
        be passed through to the extension you are registering

        :param configs: A dictionary of options for the extension being regsitered
        :param ext_cls: The class name of your extension
        """
        instance = ext_cls()
        self._instance.registerExtensions([instance], configs)
        return ext_cls
