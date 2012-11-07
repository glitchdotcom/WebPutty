import logging
from datetime import datetime
import json
from google.appengine.api import memcache
from flask import Module, request, abort, jsonify
from flaskext.csrf import csrf_exempt
from models import Page, PageChannel, Style, StyleRevision
from decorators import requires_auth, as_json

rpc = Module(__name__, 'rpc')

@rpc.route('/page/<int:page_id>/rpc', methods=['POST'])
@requires_auth
@as_json
def page_rpc(page_id):
    page = Page.get_edit_or_404(page_id)
    try:
        message = json.loads(request.form.get('message', ''))
    except Exception:
        abort(400)
    data = message.get('data', None)
    token = message.get('from', None)
    if not token or not data:
        logging.warn('RPC received no token or data.')
        abort(400)
    cmd = data.get('cmd', None)
    if not cmd:
        logging.warn('RPC received no cmd.')
        abort(400)

    channel = PageChannel.gql('WHERE token=:1', token).get()
    if not channel:
        # We've timed out the channel. User should refresh the page.
        logging.debug('Could not find token: %s', token)
        return dict(cmd='refresh')
    channel.dt_last_update = datetime.utcnow()
    channel.put()

    # Commands
    if cmd == 'open':
        page.add_channel(channel)
        page.update_locks()
        return 'OK'
    elif cmd == 'claimLock':
        page.clean_channels()
        page.add_channel_first(channel)
        page.update_locks()
        return 'OK'
    elif cmd == 'save':
        style_id = data.get('style_id', '')
        style = Style.get_edit_or_404(style_id)
        if not style.preview_rev:
            preview_rev = StyleRevision(parent=style, rev=style.published_rev.rev + 1)
            preview_rev.put()
            style.preview_rev = preview_rev
            style.put()
        log = style.preview_rev.update(data.get('scss', ''))
        publish = data.get('fPublish', False)
        preview = not publish
        if publish:
            style.published_rev = style.preview_rev
            style.preview_rev = None
            style.put()
            page_key = str(page.key())
            memcache.delete(page_key + '-css')
            memcache.delete(page_key + '-css-etag')
            page.queue_refresh()
        return jsonify({'css': page.compressed_css(preview), 'log': log})
    else:
        logging.warn('Got a bad command: %s', cmd)
        abort(400) # Bad cmd

@rpc.route('/_ah/channel/<presence>/', methods=['POST'])
@csrf_exempt
def _channel_presence(presence):
    client_id = request.form.get('from', '')
    channel = PageChannel.get_or_404(client_id=client_id)
    page = channel.page
    if presence == 'connected':
        page.add_channel(channel)
    elif presence == 'disconnected':
        page.remove_channel(channel, True)
    page.update_locks()
    return 'OK'

