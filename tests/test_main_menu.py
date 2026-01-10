import os
import sys
import unittest
from unittest import mock

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.ui import main_menu


class TestMainMenu(unittest.TestCase):
    def test_menu_options_include_required_entries(self):
        labels = [label for label, _ in main_menu.MENU_OPTIONS]
        self.assertIn("Overworld", labels)
        self.assertIn("Battle Simulator", labels)
        self.assertIn("Pixel Art Editor", labels)
        self.assertIn("Quit", labels)

    def test_quit_option_has_no_module(self):
        quit_entries = [entry for entry in main_menu.MENU_OPTIONS if entry[0] == "Quit"]
        self.assertTrue(quit_entries, "Quit option missing from menu.")
        self.assertIsNone(quit_entries[0][1])

    def test_run_module_invokes_runpy(self):
        with mock.patch.object(main_menu.runpy, "run_module") as mock_run:
            main_menu.run_module("src.overworld.overworld")
            mock_run.assert_called_once_with("src.overworld.overworld", run_name="__main__")

    def test_run_module_swallows_system_exit(self):
        with mock.patch.object(main_menu.runpy, "run_module", side_effect=SystemExit(0)):
            main_menu.run_module("src.overworld.overworld")
