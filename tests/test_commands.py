import codecs
import os
import shutil
import tempfile
from unittest import TestCase

from aider import models
from aider.commands import Commands
from aider.io import InputOutput


class TestCommands(TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.tempdir = tempfile.mkdtemp()
        os.chdir(self.tempdir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tempdir)

    def test_cmd_add(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, yes=True)
        from aider.coders import Coder

        coder = Coder.create(models.GPT35, None, io, openai_api_key="deadbeef")
        commands = Commands(io, coder)

        # Call the cmd_add method with 'foo.txt' and 'bar.txt' as a single string
        commands.cmd_add("foo.txt bar.txt")

        # Check if both files have been created in the temporary directory
        self.assertTrue(os.path.exists("foo.txt"))
        self.assertTrue(os.path.exists("bar.txt"))

    def test_cmd_add_bad_encoding(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, yes=True)
        from aider.coders import Coder

        coder = Coder.create(models.GPT35, None, io, openai_api_key="deadbeef")
        commands = Commands(io, coder)

        # Create a new file foo.bad which will fail to decode as utf-8
        with codecs.open("foo.bad", "w", encoding="iso-8859-15") as f:
            f.write("ÆØÅ")  # Characters not present in utf-8

        commands.cmd_add("foo.bad")

        self.assertEqual(coder.abs_fnames, set())

    def test_cmd_tokens(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, yes=True)
        from aider.coders import Coder

        coder = Coder.create(models.GPT35, None, io, openai_api_key="deadbeef")
        commands = Commands(io, coder)

        commands.cmd_add("foo.txt bar.txt")
        commands.cmd_tokens("")
