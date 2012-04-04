"""CSSRule implements DOM Level 2 CSS CSSRule."""
__all__ = ['CSSRule']
__docformat__ = 'restructuredtext'
__version__ = '$Id$'

import cssutils
import xml.dom

class CSSRule(cssutils.util.Base2):
    """Abstract base interface for any type of CSS statement. This includes
    both rule sets and at-rules. An implementation is expected to preserve
    all rules specified in a CSS style sheet, even if the rule is not
    recognized by the parser. Unrecognized rules are represented using the
    :class:`CSSUnknownRule` interface.
    """

    """
    CSSRule type constants.
    An integer indicating which type of rule this is.
    """
    UNKNOWN_RULE = 0 
    ":class:`cssutils.css.CSSUnknownRule` (not used in CSSOM anymore)"
    STYLE_RULE = 1
    ":class:`cssutils.css.CSSStyleRule`"
    CHARSET_RULE = 2
    ":class:`cssutils.css.CSSCharsetRule` (not used in CSSOM anymore)"
    IMPORT_RULE = 3
    ":class:`cssutils.css.CSSImportRule`"
    MEDIA_RULE = 4
    ":class:`cssutils.css.CSSMediaRule`"
    FONT_FACE_RULE = 5
    ":class:`cssutils.css.CSSFontFaceRule`"
    PAGE_RULE = 6
    ":class:`cssutils.css.CSSPageRule`"
    NAMESPACE_RULE = 10
    """:class:`cssutils.css.CSSNamespaceRule`, 
    Value has changed in 0.9.7a3 due to a change in the CSSOM spec."""
    COMMENT = 1001 # was -1, cssutils only
    """:class:`cssutils.css.CSSComment` - not in the offical spec,
    Value has changed in 0.9.7a3"""
    VARIABLES_RULE = 1008 
    """:class:`cssutils.css.CSSVariablesRule` - experimental rule
    not in the offical spec"""

    _typestrings = {UNKNOWN_RULE: u'UNKNOWN_RULE', 
                    STYLE_RULE: u'STYLE_RULE',
                    CHARSET_RULE: u'CHARSET_RULE', 
                    IMPORT_RULE: u'IMPORT_RULE',
                    MEDIA_RULE: u'MEDIA_RULE', 
                    FONT_FACE_RULE: u'FONT_FACE_RULE', 
                    PAGE_RULE: u'PAGE_RULE',                     
                    NAMESPACE_RULE: u'NAMESPACE_RULE',
                    COMMENT: u'COMMENT',
                    VARIABLES_RULE: u'VARIABLES_RULE'
                    }

    def __init__(self, parentRule=None, parentStyleSheet=None, readonly=False):
        """Set common attributes for all rules."""
        super(CSSRule, self).__init__()
        self._parent = parentRule
        self._parentRule = parentRule
        self._parentStyleSheet = parentStyleSheet
        self._setSeq(self._tempSeq())
        # must be set after initialization of #inheriting rule is done
        self._readonly = False

    def _setAtkeyword(self, akw):
        """Check if new keyword fits the rule it is used for."""
        if not self.atkeyword or (self._normalize(akw) ==
                                  self._normalize(self.atkeyword)):
            self._atkeyword = akw
        else:
            self._log.error(u'%s: Invalid atkeyword for this rule: %r' %
                            (self._normalize(self.atkeyword), akw),
                            error=xml.dom.InvalidModificationErr)

    atkeyword = property(lambda self: self._atkeyword, _setAtkeyword,
                         doc=u"Literal keyword of an @rule (e.g. ``@IMport``).")

    def _setCssText(self, cssText):
        """
        :param cssText:
            A parsable DOMString.
        :exceptions:
            - :exc:`~xml.dom.SyntaxErr`:
              Raised if the specified CSS string value has a syntax error and
              is unparsable.
            - :exc:`~xml.dom.InvalidModificationErr`:
              Raised if the specified CSS string value represents a different
              type of rule than the current one.
            - :exc:`~xml.dom.HierarchyRequestErr`:
              Raised if the rule cannot be inserted at this point in the
              style sheet.
            - :exc:`~xml.dom.NoModificationAllowedErr`:
              Raised if the rule is readonly.
        """
        self._checkReadonly()

    cssText = property(lambda self: u'', _setCssText,
                       doc=u"(DOM) The parsable textual representation of the "
                           u"rule. This reflects the current state of the rule "
                           u"and not its initial value.")

    parent = property(lambda self: self._parent,
                      doc=u"The Parent Node of this CSSRule or None.")

    parentRule = property(lambda self: self._parentRule,
                          doc=u"If this rule is contained inside another rule "
                          u"(e.g. a style rule inside an @media block), this "
                          u"is the containing rule. If this rule is not nested "
                          u"inside any other rules, this returns None.")

    def _getParentStyleSheet(self):
        # rules contained in other rules (@media) use that rules parent
        if (self.parentRule):
            return self.parentRule._parentStyleSheet
        else:
            return self._parentStyleSheet

    parentStyleSheet = property(_getParentStyleSheet,
                                doc=u"The style sheet that contains this rule.")

    type = property(lambda self: self.UNKNOWN_RULE,
                    doc=u"The type of this rule, as defined by a CSSRule "
                        u"type constant.")

    typeString = property(lambda self: CSSRule._typestrings[self.type],
                          doc=u"Descriptive name of this rule's type.")

    wellformed = property(lambda self: False,
                          doc=u"If the rule is wellformed.")
