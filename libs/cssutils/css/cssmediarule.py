"""CSSMediaRule implements DOM Level 2 CSS CSSMediaRule."""
__all__ = ['CSSMediaRule']
__docformat__ = 'restructuredtext'
__version__ = '$Id$'

import cssrule
import cssutils
import xml.dom

class CSSMediaRule(cssrule.CSSRule):
    """
    Objects implementing the CSSMediaRule interface can be identified by the
    MEDIA_RULE constant. On these objects the type attribute must return the
    value of that constant.

    Format::

      : MEDIA_SYM S* medium [ COMMA S* medium ]* 
      
          STRING? # the name
      
      LBRACE S* ruleset* '}' S*;
      
    ``cssRules``
        All Rules in this media rule, a :class:`~cssutils.css.CSSRuleList`.
    """
    def __init__(self, mediaText='all', name=None,
                 parentRule=None, parentStyleSheet=None, readonly=False):
        """constructor"""
        super(CSSMediaRule, self).__init__(parentRule=parentRule, 
                                           parentStyleSheet=parentStyleSheet)
        self._atkeyword = u'@media'
        
        # 1. media 
        if mediaText:
            self.media = mediaText
        else:
            self.media = cssutils.stylesheets.MediaList()

        self.name = name
        self.cssRules = cssutils.css.CSSRuleList()
        self._readonly = readonly

    def __iter__(self):
        """Generator iterating over these rule's cssRules."""
        for rule in self._cssRules:
            yield rule
            
    def __repr__(self):
        return u"cssutils.css.%s(mediaText=%r)" % (
                self.__class__.__name__,
                self.media.mediaText)
        
    def __str__(self):
        return u"<cssutils.css.%s object mediaText=%r at 0x%x>" % (
                self.__class__.__name__,
                self.media.mediaText,
                id(self))

    def _setCssRules(self, cssRules):
        "Set new cssRules and update contained rules refs."
        cssRules.append = self.insertRule
        cssRules.extend = self.insertRule
        cssRules.__delitem__ == self.deleteRule
        
        for rule in cssRules:
            rule._parentStyleSheet = None #self.parentStyleSheet?
            rule._parentRule = self
            
        self._cssRules = cssRules

    cssRules = property(lambda self: self._cssRules, _setCssRules,
            "All Rules in this style sheet, a "
            ":class:`~cssutils.css.CSSRuleList`.")

    def _getCssText(self):
        """Return serialized property cssText."""
        return cssutils.ser.do_CSSMediaRule(self)

    def _setCssText(self, cssText):
        """
        :param cssText:
            a parseable string or a tuple of (cssText, dict-of-namespaces)
        :Exceptions:
            - :exc:`~xml.dom.NamespaceErr`:
              Raised if a specified selector uses an unknown namespace
              prefix.
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
        # media "name"? { cssRules }
        super(CSSMediaRule, self)._setCssText(cssText)
        
        # might be (cssText, namespaces)
        cssText, namespaces = self._splitNamespacesOff(cssText)
        
        try:
            # use parent style sheet ones if available
            namespaces = self.parentStyleSheet.namespaces
        except AttributeError:
            pass
        
        tokenizer = self._tokenize2(cssText)
        attoken = self._nexttoken(tokenizer, None)
        if self._type(attoken) != self._prods.MEDIA_SYM:
            self._log.error(u'CSSMediaRule: No CSSMediaRule found: %s' %
                self._valuestr(cssText),
                error=xml.dom.InvalidModificationErr)
        
        else:            
            # save if parse goes wrong
            oldMedia = self._media
            oldName = self._name
            oldCssRules = self._cssRules
            
            ok = True

            # media
            mediatokens, end = self._tokensupto2(tokenizer, 
                                                 mediaqueryendonly=True,
                                                 separateEnd=True)        
            if u'{' == self._tokenvalue(end)\
               or self._prods.STRING == self._type(end):
                self.media = cssutils.stylesheets.MediaList(parentRule=self)
                # TODO: remove special case
                self.media.mediaText = mediatokens
                ok = ok and self.media.wellformed
            else:
                ok = False
            
            # name (optional)
            name = None
            nameseq = self._tempSeq()
            if self._prods.STRING == self._type(end):
                name = self._stringtokenvalue(end)
                # TODO: for now comments are lost after name
                nametokens, end = self._tokensupto2(tokenizer, 
                                                    blockstartonly=True,
                                                    separateEnd=True)
                wellformed, expected = self._parse(None, 
                                                   nameseq, 
                                                   nametokens, 
                                                   {})
                if not wellformed:
                    ok = False
                    self._log.error(u'CSSMediaRule: Syntax Error: %s' % 
                                    self._valuestr(cssText))
                    

            # check for {
            if u'{' != self._tokenvalue(end):
                self._log.error(u'CSSMediaRule: No "{" found: %s' % 
                                self._valuestr(cssText))
                return
            
            # cssRules
            cssrulestokens, braceOrEOF = self._tokensupto2(tokenizer, 
                                               mediaendonly=True,
                                               separateEnd=True)
            nonetoken = self._nexttoken(tokenizer, None)
            if 'EOF' == self._type(braceOrEOF):
                # HACK!!!
                # TODO: Not complete, add EOF to rule and } to @media
                cssrulestokens.append(braceOrEOF)
                braceOrEOF = ('CHAR', '}', 0, 0)
                self._log.debug(u'CSSMediaRule: Incomplete, adding "}".', 
                                token=braceOrEOF, neverraise=True)

            if u'}' != self._tokenvalue(braceOrEOF):
                self._log.error(u'CSSMediaRule: No "}" found.', 
                                token=braceOrEOF)
            elif nonetoken:
                self._log.error(u'CSSMediaRule: Trailing content found.',
                                token=nonetoken)
            else:                
                # for closures: must be a mutable
                new = {'wellformed': True }
                                   
                def COMMENT(expected, seq, token, tokenizer=None):
                    self.insertRule(cssutils.css.CSSComment([token],
                                                            parentRule=self,
                                                            parentStyleSheet=self.parentStyleSheet))
                    return expected

                def ruleset(expected, seq, token, tokenizer):
                    rule = cssutils.css.CSSStyleRule(parentRule=self,
                                                     parentStyleSheet=self.parentStyleSheet)
                    rule.cssText = self._tokensupto2(tokenizer, token)
                    if rule.wellformed:
                        self.insertRule(rule)
                    return expected
        
                def atrule(expected, seq, token, tokenizer):
                    # TODO: get complete rule!
                    tokens = self._tokensupto2(tokenizer, token)
                    atval = self._tokenvalue(token)
                    if atval in ('@charset ', '@font-face', '@import', 
                                 '@namespace', '@page', '@media', '@variables'):
                        self._log.error(u'CSSMediaRule: This rule is not '
                                        u'allowed in CSSMediaRule - ignored: '
                                        u'%s.' % self._valuestr(tokens),
                                        token = token, 
                                        error=xml.dom.HierarchyRequestErr)
                    else:
                        rule = cssutils.css.CSSUnknownRule(tokens,
                                                           parentRule=self, 
                                        parentStyleSheet=self.parentStyleSheet)
                        if rule.wellformed:
                            self.insertRule(rule)
                    return expected
                
                # save for possible reset
                oldCssRules = self.cssRules
                
                self.cssRules = cssutils.css.CSSRuleList()
                seq = [] # not used really
                
                tokenizer = (t for t in cssrulestokens) # TODO: not elegant!
                wellformed, expected = self._parse(braceOrEOF, 
                                                   seq, 
                                                   tokenizer, {
                                                     'COMMENT': COMMENT,
                                                     'CHARSET_SYM': atrule,
                                                     'FONT_FACE_SYM': atrule,
                                                     'IMPORT_SYM': atrule,
                                                     'NAMESPACE_SYM': atrule,
                                                     'PAGE_SYM': atrule,
                                                     'MEDIA_SYM': atrule,
                                                     'ATKEYWORD': atrule
                                                   }, 
                                                   default=ruleset,
                                                   new=new)
                ok = ok and wellformed
                
            if ok:
                self.name = name
                self._setSeq(nameseq)
            else:
                self._media = oldMedia
                self._cssRules = oldCssRules
                                            
    cssText = property(_getCssText, _setCssText,
                       doc=u"(DOM) The parsable textual representation of this "
                           u"rule.")

    def _setName(self, name):
        if isinstance(name, basestring) or name is None:
            # "" or ''
            if not name:
                name = None

            self._name = name
        else:
            self._log.error(u'CSSImportRule: Not a valid name: %s' % name)

    name = property(lambda self: self._name, _setName,
                    doc=u"An optional name for this media rule.")

    def _setMedia(self, media):
        """
        :param media:
            a :class:`~cssutils.stylesheets.MediaList` or string
        """
        self._checkReadonly()
        if isinstance(media, basestring):
            self._media = cssutils.stylesheets.MediaList(mediaText=media, 
                                                         parentRule=self)
        else:
            media._parentRule = self
            self._media = media
        
        # NOT IN @media seq at all?!
#        # update seq
#        for i, item in enumerate(self.seq):
#            if item.type == 'media':
#                self._seq[i] = (self._media, 'media', None, None)
#                break
#        else:
#            # insert after @media if not in seq at all
#            self.seq.insert(0, 
#                             self._media, 'media', None, None)
            
    media = property(lambda self: self._media, _setMedia,
                     doc=u"(DOM) A list of media types for this rule "
                         u"of type :class:`~cssutils.stylesheets.MediaList`.")
    
    def deleteRule(self, index):
        """
        Delete the rule at `index` from the media block.
        
        :param index:
            The `index` of the rule to be removed from the media block's rule
            list. For an `index` < 0 **no** :exc:`~xml.dom.IndexSizeErr` is
            raised but rules for normal Python lists are used. E.g. 
            ``deleteRule(-1)`` removes the last rule in cssRules.
            
            `index` may also be a CSSRule object which will then be removed
            from the media block.

        :Exceptions:
            - :exc:`~xml.dom.IndexSizeErr`:
              Raised if the specified index does not correspond to a rule in
              the media rule list.
            - :exc:`~xml.dom.NoModificationAllowedErr`:
              Raised if this media rule is readonly.
        """
        self._checkReadonly()

        if isinstance(index, cssrule.CSSRule):
            for i, r in enumerate(self.cssRules):
                if index == r:
                    index = i
                    break
            else:
                raise xml.dom.IndexSizeErr(u"CSSMediaRule: Not a rule in "
                                           u"this rule'a cssRules list: %s"
                                           % index)

        try:
            self._cssRules[index]._parentRule = None # detach
            del self._cssRules[index] # remove from @media
        except IndexError:
            raise xml.dom.IndexSizeErr(u'CSSMediaRule: %s is not a valid index '
                                       u'in the rulelist of length %i' 
                                       % (index, self._cssRules.length))

    def add(self, rule):
        """Add `rule` to end of this mediarule. 
        Same as :meth:`~cssutils.css.CSSMediaRule.insertRule`."""
        self.insertRule(rule, index=None)
            
    def insertRule(self, rule, index=None):
        """
        Insert `rule` into the media block.
        
        :param rule:
            the parsable text representing the `rule` to be inserted. For rule
            sets this contains both the selector and the style declaration. 
            For at-rules, this specifies both the at-identifier and the rule
            content.

            cssutils also allows rule to be a valid 
            :class:`~cssutils.css.CSSRule` object.

        :param index:
            before the specified `rule` will be inserted. 
            If the specified `index` is
            equal to the length of the media blocks's rule collection, the
            rule will be added to the end of the media block.
            If index is not given or None rule will be appended to rule
            list.

        :returns:
            the index within the media block's rule collection of the
            newly inserted rule.

        :exceptions:
            - :exc:`~xml.dom.HierarchyRequestErr`:
              Raised if the `rule` cannot be inserted at the specified `index`,
              e.g., if an @import rule is inserted after a standard rule set
              or other at-rule.
            - :exc:`~xml.dom.IndexSizeErr`:
              Raised if the specified `index` is not a valid insertion point.
            - :exc:`~xml.dom.NoModificationAllowedErr`:
              Raised if this media rule is readonly.
            - :exc:`~xml.dom.SyntaxErr`:
              Raised if the specified `rule` has a syntax error and is
              unparsable.

        """
        self._checkReadonly()

        # check position
        if index is None:
            index = len(self._cssRules)
        elif index < 0 or index > self._cssRules.length:
            raise xml.dom.IndexSizeErr(u'CSSMediaRule: Invalid index %s for '
                                       u'CSSRuleList with a length of %s.'
                                       % (index, self._cssRules.length))

        # parse
        if isinstance(rule, basestring):
            tempsheet = cssutils.css.CSSStyleSheet()
            tempsheet.cssText = rule
            if len(tempsheet.cssRules) != 1 or (tempsheet.cssRules and
             not isinstance(tempsheet.cssRules[0], cssutils.css.CSSRule)):
                self._log.error(u'CSSMediaRule: Invalid Rule: %s' % rule)
                return
            rule = tempsheet.cssRules[0]
            
        elif isinstance(rule, cssutils.css.CSSRuleList):
            # insert all rules
            for i, r in enumerate(rule):
                self.insertRule(r, index + i)
            return index
            
        elif not isinstance(rule, cssutils.css.CSSRule):
            self._log.error(u'CSSMediaRule: Not a CSSRule: %s' % rule)
            return

        # CHECK HIERARCHY
        # @charset @import @page @namespace @media
        if isinstance(rule, cssutils.css.CSSCharsetRule) or \
           isinstance(rule, cssutils.css.CSSFontFaceRule) or \
           isinstance(rule, cssutils.css.CSSImportRule) or \
           isinstance(rule, cssutils.css.CSSNamespaceRule) or \
           isinstance(rule, cssutils.css.CSSPageRule) or \
           isinstance(rule, CSSMediaRule):
            self._log.error(u'CSSMediaRule: This type of rule is not allowed '
                            u'here: %s' % rule.cssText,
                            error=xml.dom.HierarchyRequestErr)
            return

        self._cssRules.insert(index, rule)
        rule._parentRule = self
        rule._parentStyleSheet = self.parentStyleSheet
        return index

    type = property(lambda self: self.MEDIA_RULE, 
                    doc=u"The type of this rule, as defined by a CSSRule "
                        u"type constant.")

    wellformed = property(lambda self: self.media.wellformed)
