import logging
import settings
from textwrap import dedent
from google.appengine.ext import webapp
from google.appengine.api import mail
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

class ReceiveEmail(InboundMailHandler):
    def receive(self,message):
        headers = dedent("""\
            From: %s
            To: %s
            Subject: %s
            """ % (
                message.sender,
                message.to,
                message.subject,
            ))

        log_msg = headers + 'Body:\n'
        for content_type, body in message.bodies():
            log_msg += '%s\n%s\n-------------------------------\n' % (content_type, body.decode())

        if settings.log_all_incoming:
            logging.info(log_msg)

        email_subject = '%s (from %s)' % (message.subject, message.sender)

        email_body = headers
        for content_type, body in message.bodies('text/plain'):
            email_body += body.decode()

        email_html = '<p>' + headers.replace('\n', '<br />') + '</p>'
        for content_type, body in message.bodies('text/html'):
            email_html += body.decode()

        mail.send_mail(
            sender = settings.incoming_sender_email,
            reply_to = message.sender,
            to = settings.forward_mail_to,
            subject = email_subject,
            body = email_body,
            html = email_html,
        )
        return 'OK'

application = webapp.WSGIApplication([ReceiveEmail.mapping()], debug=True)
