import os
import sys
import unittest
from unittest import mock


from src.ui import main_menu


class TestMainMenu(unittest.TestCase):
    def test_menu_options_include_required_entries(self):
        labels = [label for label, _ in main_menu.MENU_OPTIONS]
        self.assertIn("Overworld", labels)
        self.assertIn("Battle Simulator", labels)
        self.assertIn("Pixel Art Editor", labels)
        self.assertIn("Move Animation Editor", labels)
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

    def test_init_menu_clears_resource_cache_before_loading_fonts(self):
        resource_manager = mock.Mock()
        resource_manager.get_font.side_effect = ["title-font", "option-font"]
        fake_screen = object()
        fake_clock = object()

        with (
            mock.patch.object(main_menu.pygame, "init") as pygame_init,
            mock.patch.object(main_menu.pygame.display, "set_mode", return_value=fake_screen) as set_mode,
            mock.patch.object(main_menu.pygame.display, "set_caption") as set_caption,
            mock.patch.object(main_menu.pygame.time, "Clock", return_value=fake_clock) as clock_ctor,
            mock.patch.object(main_menu, "get_resource_manager", return_value=resource_manager) as get_rm,
        ):
            screen, title_font, option_font, clock = main_menu.init_menu()

        pygame_init.assert_called_once_with()
        set_mode.assert_called_once_with((main_menu.config.MENU_WIDTH, main_menu.config.MENU_HEIGHT))
        set_caption.assert_called_once_with("PokeClone")
        get_rm.assert_called_once_with()
        resource_manager.clear.assert_called_once_with()
        resource_manager.get_font.assert_has_calls(
            [
                mock.call(main_menu.config.DEFAULT_FONT, main_menu.config.MENU_TITLE_FONT_SIZE),
                mock.call(main_menu.config.DEFAULT_FONT, main_menu.config.MENU_OPTION_FONT_SIZE),
            ]
        )
        clock_ctor.assert_called_once_with()
        self.assertIs(screen, fake_screen)
        self.assertEqual(title_font, "title-font")
        self.assertEqual(option_font, "option-font")
        self.assertIs(clock, fake_clock)
