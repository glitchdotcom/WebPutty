from flask import request

from werkzeug import FileStorage

from wtforms import FileField as _FileField
from wtforms import ValidationError

def is_file(field):

    return isinstance(field.data, FileStorage) and \
        field.data.filename is not None


class FileField(_FileField):
    """
    Subclass of **wtforms.FileField** providing a `file` property
    returning the relevant **FileStorage** instance in **request.files**.
    """
    @property
    def file(self):
        """
        :deprecated: synonym for **data**
        """
        return self.data


class FileRequired(object):
    """
    Validates that field has a **FileStorage** instance
    attached.

    `message` : error message

    You can also use the synonym **file_required**.
    """

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if not is_file(field):
            raise ValidationError, self.message

file_required = FileRequired


class FileAllowed(object):
    """
    Validates that the uploaded file is allowed by the given
    Flask-Uploads UploadSet.

    `upload_set` : instance of **flaskext.uploads.UploadSet**

    `message`    : error message

    You can also use the synonym **file_allowed**.
    """

    def __init__(self, upload_set, message=None):
        self.upload_set = upload_set
        self.message = message

    def __call__(self, form, field):

        if not is_file(field):
            return

        if not self.upload_set.file_allowed(
            field.data, field.data.filename):
            raise ValidationError, self.message


file_allowed = FileAllowed
    
