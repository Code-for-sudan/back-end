import os
import tempfile
import unittest
from unittest import mock
from ..utils import delete_email_files

class TestDeleteEmailFiles(unittest.TestCase):

    def setUp(self):
        # Create temporary files for html, plain, attachments, images, styles
        self.temp_files = []
        for _ in range(7):
            fd, path = tempfile.mkstemp()
            os.close(fd)
            self.temp_files.append(path)

    def tearDown(self):
        # Cleanup in case files weren't deleted
        for f in self.temp_files:
            if os.path.exists(f):
                os.remove(f)

    def test_delete_email_files_deletes_all_files(self):
        html_path, plain_path, att1, att2, img1, style1, style2 = self.temp_files
        delete_email_files(
            html_path,
            plain_path,
            attachment_paths=[att1, att2],
            image_paths=[img1],
            style_paths=[style1, style2]
        )
        for f in self.temp_files:
            self.assertFalse(os.path.exists(f))

    def test_delete_email_files_ignores_nonexistent_files(self):
        html_path = "/tmp/nonexistent_html_file"
        plain_path = "/tmp/nonexistent_plain_file"
        att = "/tmp/nonexistent_attachment"
        img = "/tmp/nonexistent_image"
        style = "/tmp/nonexistent_style"
        # Should not raise
        try:
            delete_email_files(
                html_path,
                plain_path,
                attachment_paths=[att],
                image_paths=[img],
                style_paths=[style]
            )
        except Exception as e:
            self.fail(f"delete_email_files raised an exception: {e}")

    def test_delete_email_files_handles_delete_exception(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "file.txt")
            with open(file_path, "w") as f:
                f.write("test")
            with mock.patch("os.remove", side_effect=PermissionError("No permission")):
                with self.assertLogs(logger='email', level='INFO') as log:
                    delete_email_files(file_path, None)
            # File should still exist
            self.assertTrue(os.path.exists(file_path))

    def test_delete_email_files_with_none_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "file.txt")
            with open(file_path, "w") as f:
                f.write("test")
            delete_email_files(file_path, None, attachment_paths=None, image_paths=None, style_paths=None)
            self.assertFalse(os.path.exists(file_path))
