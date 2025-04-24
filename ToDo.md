# PokeClone Project KANBAN Board (Detailed - 2025-04-06 v6)

---

## To Do

### Highest Priority

### High Priority

### Medium Priority

* **[UI-BATTLESIM-NAVHINT] Add Page Navigation Key Hints in Battle Sim Character Select**
    * **Type:** Improvement / UI
    * **Priority:** Medium
    * **Description:** In the battle simulator's character selection screen, when the user attempts to navigate left off the first item on a page or right off the last item on a page using arrow keys, display a temporary visual hint (e.g., "Press [ for Prev Page" or "Press ] for Next Page") to guide them on how to change pages.
    * **Acceptance Criteria:**
        * Pressing Left Arrow on the first selectable item displays the previous page hint (if applicable).
        * Pressing Right Arrow on the last selectable item displays the next page hint (if applicable).
        * The hint is displayed clearly on the screen (e.g., near page number or center).
        * The hint disappears after a short duration (e.g., 1-2 seconds) or on the next user input.
        * The core navigation logic remains unchanged.
        * **Testing:** Manual testing confirms hints appear correctly at page edges and disappear appropriately.
    * **Labels:** `ui`, `ux`, `battle-system`, `improvement`, `input`

* **[POKE-10] Refactor Pixel Art Editor for Modularity**
    * **Type:** Task / Improvement
    * **Priority:** Medium
    * **Description:** The main file for the pixel art editor, `pixle_art_editor.py`, has grown very large... (previous description remains) ...Refactor the `Editor` class and `handle_event` method to delegate responsibilities to these new components.
    * **Acceptance Criteria:**
        * The codebase for the pixel editor is organized into multiple smaller, well-defined modules/classes.
        * The main editor file (`pixle_art_editor.py` or its replacement) is significantly shorter and less complex.
        * Responsibilities are clearly separated (e.g., tool logic is separate from UI drawing).
        * The editor's functionality remains intact or is improved.
        * Code is more readable and maintainable.
        * **Testing:** Integration tests are *written and pass*, confirming that the refactored modules work together correctly within the main application loop.
        * **Testing:** Manual regression testing confirms all previous editor functionalities work as expected after refactoring.
    * **Labels:** `refactoring`, `editor`, `code-quality`, `maintainability`, `architecture`

* **[POKE-11] Improve Pixel Editor UI/UX Feedback**
    * **Type:** Improvement
    * **Priority:** Medium
    * **Description:** The pixel art editor currently lacks some key visual feedback... (previous description remains) ...Review and correct the panning logic to use standard mouse wheel events (`event.y` for vertical) and potentially implement panning via middle-mouse drag or keyboard modifiers + mouse drag for more control.
    * **Acceptance Criteria:**
        * The currently selected drawing/editing tool is clearly indicated visually.
        * Zooming feels intuitive, potentially centering on the cursor.
        * Panning works predictably using standard controls.
        * **Testing:** Manual testing confirms that the visual indicator for the active tool is present and updates correctly.
        * **Testing:** Manual testing confirms that zoom behavior is intuitive and centers correctly (either on view or cursor, as implemented).
        * **Testing:** Manual testing confirms that panning controls work as expected and feel natural.
    * **Labels:** `ui`, `ux`, `editor`, `improvement`, `input`

* **[POKE-12] Enhance Opponent Battle AI**
    * **Type:** Improvement
    * **Priority:** Medium
    * **Description:** The current AI for the opponent in `battle_simulator.py` (`opponent_choose_move` function) is extremely basic... (previous description remains) ...Start by implementing basic type effectiveness considerations and perhaps HP awareness.
    * **Acceptance Criteria:**
        * The `opponent_choose_move` function uses game state information (e.g., types, HP) to make move decisions.
        * The opponent's behavior is noticeably more strategic than pure random selection.
        * The complexity can be increased incrementally.
        * **Testing:** Manual playtesting across several battles confirms the AI makes decisions that are more strategic than random.
        * **Testing:** Unit/integration tests (if applicable to the AI logic modules) are *written and pass*, verifying correct processing of game state.
    * **Labels:** `battle-system`, `ai`, `improvement`, `gameplay`

* **[POKE-13] Implement Battle Sound Effects**
    * **Type:** Task
    * **Priority:** Medium
    * **Description:** While the game has background music functionality (`battle_simulator.py` `play_random_song`), it lacks sound effects... (previous description remains) ...Ensure multiple sounds can play without cutting each other off abruptly (Pygame's mixer handles channels automatically to some extent).
    * **Acceptance Criteria:**
        * Sound effect files are present in the `sounds/` directory.
        * Sounds are loaded using `pygame.mixer.Sound`.
        * Key battle events (attacks, damage, faints, stat changes, win/loss) trigger corresponding sound effects.
        * Sound effects enhance the battle experience.
        * **Testing:** Manual testing confirms that appropriate sounds play at the correct times during battle sequences and that sounds do not excessively overlap or cut each other off.
    * **Labels:** `audio`, `battle-system`, `feature`, `immersion`, `ux`

* **[POKE-14] Refine Editor Tool State Management (Select/Paste/Mirror/Rotate)**
    * **Type:** Improvement / Bug
    * **Priority:** Medium
    * **Description:** Managing the editor's current mode (e.g., 'draw', 'select', 'paste') and how tools interact with these modes seems complex... (previous description remains) ...Refactor the `handle_event` and related functions to adhere to this explicit state management logic. This might be done as part of POKE-10.
    * **Acceptance Criteria:**
        * Editor modes (Draw, Select, Fill, Paste) and tool activations follow clear, predictable rules.
        * State transition logic is centralized or clearly managed.
        * Interactions like selecting colors or clicking buttons have consistent effects on the current mode.
        * Paste mode allows multiple placements until explicitly cancelled.
        * Using Copy, Mirror, Rotate behaves logically with respect to the active selection and mode.
        * **Testing:** Manual testing confirms that switching between tools and modes behaves predictably according to the defined rules.
        * **Testing:** Unit tests for the state machine/manager logic are *written and pass*.
    * **Labels:** `editor`, `state-management`, `refactoring`, `ux`, `bug`, `architecture`
    * **Depends On:** POKE-10 (potentially)

* **[TEST-1] Set up Unit Testing Framework**
    * **Type:** Task
    * **Priority:** Medium
    * **Description:** The project currently lacks automated tests... (previous description remains) ...Ensure basic setup allows tests to be written and executed easily.
    * **Acceptance Criteria:**
        * A testing framework (`unittest` or `pytest`) is added as a development dependency.
        * Project structure includes a dedicated `tests/` directory.
        * A sample test runs successfully using the framework's runner (e.g., `python -m unittest discover` or `pytest`).
        * Instructions for running tests are added (e.g., to README or a CONTRIBUTING guide).
        * **Testing:** Running the test runner executes the sample test and reports success. (AC inherently covers testing).
    * **Labels:** `testing`, `infrastructure`, `code-quality`

* **[TEST-2] Write Unit Tests for Damage Calculation Logic**
    * **Type:** Task
    * **Priority:** Medium
    * **Description:** The `calculate_damage` function in `battle_simulator.py` contains critical game logic... (previous description remains) ...(Optional) Mocking `random.uniform` to test the damage range calculation deterministically.
    * **Acceptance Criteria:**
        * A test suite exists for `calculate_damage`.
        * Tests cover various type effectiveness scenarios.
        * Tests cover stat-changing moves (0 power).
        * Tests pass reliably.
        * **Testing:** Running the test suite executes all *written* damage calculation tests and reports success. (AC inherently covers testing).
    * **Labels:** `testing`, `battle-system`, `code-quality`
    * **Depends On:** TEST-1, POKE-5 (for effectiveness values)

* **[TEST-3] Write Unit Tests for Stat Modification Logic**
    * **Type:** Task
    * **Priority:** Medium
    * **Description:** The `apply_stat_change` function (and potentially the underlying formula if POKE-7 is done) in `battle_simulator.py` modifies creature stats... (previous description remains) ...Potential edge cases (e.g., hitting max/min stat stages if implemented).
    * **Acceptance Criteria:**
        * A test suite exists for stat modification logic.
        * Tests cover buffs and debuffs for relevant stats.
        * Tests validate the calculated stat values against expected outcomes based on the implemented formula/stage system.
        * Tests pass reliably.
        * **Testing:** Running the test suite executes all *written* stat modification tests and reports success. (AC inherently covers testing).
    * **Labels:** `testing`, `battle-system`, `code-quality`
    * **Depends On:** TEST-1

### Low Priority

* **[POKE-15] Remove Magic Numbers from Codebase**
    * **Type:** Task / Improvement
    * **Priority:** Low
    * **Description:** Throughout the codebase (especially in UI layout calculations...) ... (previous description remains) ...The goal is to improve code readability and make future adjustments easier.
    * **Acceptance Criteria:**
        * Hardcoded numerical literals with unclear meaning are replaced by named constants.
        * Code readability is improved.
        * **Testing:** Code review confirms removal of magic numbers.
        * **Testing:** Manual regression testing confirms the changes haven't introduced functional bugs.
    * **Labels:** `code-quality`, `refactoring`, `maintainability`

* **[POKE-16] Add Robust Error Handling**
    * **Type:** Task / Improvement
    * **Priority:** Low
    * **Description:** While some basic error handling exists... (previous description remains) ...Ensure user actions like cancelling dialogs don't cause errors.
    * **Acceptance Criteria:**
        * Common file I/O errors are caught and handled gracefully.
        * Potential Pygame errors in critical sections are handled.
        * The application provides user feedback on errors where appropriate, rather than just crashing.
        * **Testing:** Manual testing involves attempting to trigger expected errors (e.g., deleting a required file, read-only permissions, cancelling save dialogs) and verifying the application handles them gracefully without crashing.
        * **Testing:** Code review confirms appropriate `try...except` blocks are added.
    * **Labels:** `code-quality`, `robustness`, `error-handling`, `ux`

* **[POKE-17] Add Missing README Screenshot and Documentation**
    * **Type:** Task
    * **Priority:** Low
    * **Description:** The project's `README.md` file currently has placeholders... (previous description remains) ...Either add relevant developer/user documentation under the "Documentation" section or remove the section if no additional documentation is planned beyond the README itself.
    * **Acceptance Criteria:**
        * The screenshot path in `README.md` points to an actual, relevant image file committed to the repository.
        * The "Documentation" section is either populated or removed.
        * The README accurately reflects the project's current state.
        * **Testing:** Manual visual inspection of the rendered `README.md` confirms the screenshot displays correctly and the documentation section is appropriately handled.
    * **Labels:** `documentation`, `readme`, `assets`

* **[POKE-18] Optimize Editor Undo/Redo Memory Usage**
    * **Type:** Improvement
    * **Priority:** Low
    * **Description:** The pixel editor's undo/redo system (`pixle_art_editor.py` `save_state`, `undo`, `redo` methods) currently works by saving complete copies... (previous description remains) ...This is likely a significant refactoring effort and should only be undertaken if memory usage proves problematic.
    * **Acceptance Criteria:**
        * (If implemented) The undo/redo system consumes measurably less memory per step, especially for large canvases.
        * Undo/Redo functionality remains correct and reliable for all editing operations.
        * **Testing:** Performance testing compares memory usage before and after optimization under heavy editing scenarios.
        * **Testing:** Manual regression testing confirms undo/redo still works correctly for all tools and actions after optimization. Relevant unit tests (if applicable to the optimization logic) are *written/updated and pass*.
    * **Labels:** `editor`, `performance`, `memory`, `optimization`, `improvement`, `refactoring`

* **[POKE-19] Adjust Creature Sprite Positioning in Battle View**
    * **Type:** Improvement
    * **Priority:** Low
    * **Description:** In the battle screen (`battle_simulator.py` `draw_battle` function), the creature sprites are drawn using coordinates calculated relative to the bottom of the screen... (previous description remains) ...Experiment with different positioning strategies or offsets for the creature sprites...
    * **Acceptance Criteria:**
        * Creature sprite positions in the battle view are visually appealing and well-integrated with other UI elements.
        * Positioning logic is clear and potentially uses constants from POKE-1 (Done).
        * **Testing:** Manual visual inspection confirms the new layout looks good across different potential sprite sizes (if applicable) and screen resolutions (if relevant).
    * **Labels:** `ui`, `ux`, `battle-system`, `visuals`, `improvement`

* **[POKE-20] Perform Balance Pass on Stat Changes and Damage**
    * **Type:** Task / Improvement
    * **Priority:** Low
    * **Description:** After implementing changes to the stat modification formula (POKE-7 - Done) and completing the type chart (POKE-5), the overall balance of combat needs review... (previous description remains) ...Adjust base stats (`monsters.json`), move powers (`moves.json`), stat change magnitudes (POKE-7 logic - Done), or type effectiveness multipliers (POKE-5 data) as needed...
    * **Acceptance Criteria:**
        * Combat feels relatively balanced – no single type or strategy is overwhelmingly dominant without counterplay.
        * Stat changes have a noticeable but not game-breaking impact.
        * Battles last a reasonable number of turns on average.
        * Adjustments to data files (`monsters.json`, `moves.json`, `type_chart.json`) or formulas are documented.
        * **Testing:** Extensive playtesting by one or more individuals confirms the subjective feel of balance and identifies any remaining dominant strategies or frustrating mechanics. Playtest results are summarized.
    * **Labels:** `balancing`, `gameplay`, `battle-system`, `improvement`, `testing`
    * **Depends On:** POKE-5

---

## In Progress

* **[POKE-9] Replace Tkinter Dialogs with Native Pygame UI or Library**
    * **Type:** Improvement / Task
    * **Priority:** Medium
    * **Description:** The pixel art editor (`pixle_art_editor.py`) currently relies on Python's built-in Tkinter library... (previous description remains) ...This involves creating custom input fields, buttons, file browsers, and color pickers that work within the Pygame event loop and rendering system.
    * **Acceptance Criteria:**
        * File opening, saving, color picking, and initial mode selection are handled entirely within the Pygame window environment.
        * The Tkinter import and its usage are removed from `pixle_art_editor.py`.
        * Window focus problems associated with external dialogs are resolved.
        * The UI for these functions feels integrated with the rest of the editor.
        * **Testing:** Manual tests confirm the new UI elements function correctly, reliably, and that focus issues are gone; relevant integration tests (if applicable, e.g., for a GUI library) are *written and pass*.
    * **Labels:** `ui`, `ux`, `refactoring`, `editor`, `dependencies`, `improvement`

---

## Done

* **[FEAT-REFIMG] Add Reference Image Layer to Pixel Editor**
    * **Type:** Feature
    * **Priority:** Medium (Adjust as needed)
    * **Description:** Implement functionality to load, display (with aspect-fit scaling), adjust transparency (alpha slider), and clear a background reference/tracing image within the pixel art editor's monster editing mode. The image should appear behind the interactive pixel grid.
    * **Acceptance Criteria:**
        * A "Load Ref Img" button/option allows selecting PNG/JPG/etc. files.
        * The loaded image displays behind the *active* sprite editor grid, scaled to fit while maintaining aspect ratio.
        * An alpha slider controls the reference image's transparency (0-100% or 0-255).
        * A "Clear Ref Img" button/option removes the reference image.
        * Loading, clearing, and alpha adjustment work correctly without breaking other editor functions.
        * Drawing/erasing on the main grid is unaffected by the reference image.
        * **Testing:** Manual testing confirms loading various image types, correct display/scaling, functional alpha slider, and clearing functionality.
        * **Testing:** Manual testing confirms drawing on the main canvas is not blocked.
        * **Testing:** Unit tests pass (mocking GUI interactions).
    * **Labels:** `feature`, `editor`, `ui`, `ux`, `reference-image`

* **[POKE-1] Define and Centralize Core Configuration Constants** (Type: Task, Priority: Highest)
* **[POKE-2] Refactor Sprite Creation to Use Native Resolution** (Type: Bug / Improvement, Priority: Highest)
* **[POKE-3] Refactor Editor Sprite Loading/Saving to Native Resolution** (Type: Bug / Improvement, Priority: Highest)
* **[POKE-4] Refactor Battle Sim Sprite Loading/Scaling** (Type: Bug / Improvement, Priority: Highest)
* **[POKE-5] Complete `type_chart.json` Data** (Type: Bug / Data, Priority: High)
* **[POKE-6] Implement Stat Reset Between Battles** (Type: Bug, Priority: High)
* **[POKE-7] Review and Simplify Stat Change Formula** (Type: Improvement / Bug, Priority: High)
* **[POKE-8] Fix Creature Selection Keyboard Navigation** (Type: Bug, Priority: High)
* **[POKE-21] Editor: Eraser/Fill modes deactivate immediately upon button click** (Type: Bug, Priority: High)

---
