# PokeClone Project KANBAN Board (Detailed - 2025-04-06 v6)

---

## To Do

### Highest Priority

* **[OVERWORLD-1] Implement Basic Overworld Functionality (Completed)**
    * **Type:** Feature
    * **Priority:** Highest
    * **Description:** Establish the foundational overworld gameplay loop and architecture. This milestone introduces a new "Overworld" game mode, distinct from the battle simulator and pixel art editor, and accessible via a main menu. The overworld will serve as the player's primary navigation and exploration interface, laying the groundwork for future features such as encounters, NPCs, and map-based events.
    * **Scope:**
        * **Game Loop & State Management:**  
          - Create a dedicated overworld state within the main application, with clear transitions to/from other modes (battle, editor, main menu).
          - Implement a basic game loop for the overworld, handling input, updates, and rendering.
        * **Player Character:**  
          - Define a player avatar (sprite or placeholder) that can be moved around the map using keyboard input (e.g., arrow keys or WASD).
          - Track player position and direction.
        * **Map Structure:**  
          - Design a simple tile-based map system (e.g., 2D grid of tiles, loaded from a JSON or CSV file).
          - Support for at least one sample map with walkable and non-walkable tiles (e.g., walls, grass, water).
          - Render the map and player character to the screen.
        * **Movement & Collision:**  
          - Implement basic movement logic, including collision detection with impassable tiles.
          - Smooth or grid-based movement (choose one for initial implementation).
        * **Interactions:**  
          - Allow the player to interact with the environment (e.g., pressing a key to trigger an action or display a message when facing an interactive tile).
          - Placeholder for future NPC or object interactions.
        * **Mode Switching:**  
          - Add a main menu option to enter the overworld mode.
          - Provide a way to exit back to the main menu.
    * **Acceptance Criteria:**
        * The player can enter the overworld mode from the main menu.
        * The overworld displays a map and a controllable player character.
        * Player movement is responsive and respects map boundaries/collisions.
        * At least one type of interactive tile or object is present (even if only as a placeholder).
        * The player can return to the main menu from the overworld.
        * The code is organized to allow future expansion (e.g., adding NPCs, wild encounters, map transitions).
    * **Testing:**
        * Manual testing confirms all acceptance criteria.
        * Unit tests cover overworld state movement, collision, and interaction logic.
    * **Implementation Notes (Completed):**
        * Added a dedicated overworld state module (map, player, movement, interactions).
        * Implemented a pygame overworld runner with a tile map, player movement, and message prompts.
        * Added a main menu entrypoint that can launch overworld, battle simulator, or pixel art editor.
        * Added a basic message box for interactive tiles and ESC to return to the main menu.
    * **Labels:** `feature`, `overworld`, `gameplay`, `architecture`, `core`, `map`, `player`, `input`

* **[OVERWORLD-6] Implement Overworld Runtime (per design doc)**
    * **Type:** Feature
    * **Priority:** Highest
    * **Description:** Implement/align the overworld runtime systems according to `docs/overworld-system-design.md` so the game has a stable, testable contract that tooling (map editor, tile manager, audio) can target.
    * **Acceptance Criteria:**
        * The runtime behavior matches `docs/overworld-system-design.md` for movement, collision, interactions, triggers/actions, connections/portals, and per-map audio.
        * The overworld consumes the map schema defined in `docs/map-editor-design.md` without manual data edits.
        * **Testing:** Unit/integration tests cover collision, trigger ordering, connection transitions, and music switching as described in the design doc.
    * **Labels:** `feature`, `overworld`, `runtime`, `architecture`, `gameplay`


### High Priority

* **[OVERWORLD-3] Implement Map Editor (per design doc)**
    * **Type:** Feature
    * **Priority:** High
    * **Description:** Build the overworld map editor according to `docs/map-editor-design.md`, enabling creation, editing, saving, and loading of maps that the overworld runtime can consume.
    * **Acceptance Criteria:**
        * The implementation follows `docs/map-editor-design.md` (UX, data model, validation, and integration points).
        * The editor can create, edit, save, and load maps that the overworld can render and navigate without errors.
        * **Testing:** Manual end-to-end test per the workflow described in `docs/map-editor-design.md`.
    * **Labels:** `feature`, `overworld`, `map`, `editor`, `tools`

* **[OVERWORLD-4] Extend Pixel Art Editor for Tiles + Tile Manager**
    * **Type:** Feature
    * **Priority:** High
    * **Description:** Extend the existing pixel art editor to support tile-focused editing, plus add a tile manager system to edit, save, load, and reference tiles used by the overworld. This system should enable creating tile sets and linking tiles to in-game maps.
    * **Acceptance Criteria:**
        * The existing pixel art editor includes a tile-editing mode or workflow to create and edit individual tiles at a fixed tile size.
        * Tile sets can be saved and loaded from disk with metadata (e.g., tile IDs, names, properties).
        * A tile manager (integrated with or adjacent to the editor UI) provides a way to browse and select tiles for use in the map editor.
        * Overworld maps can reference tiles by stable IDs from the tile set.
        * **Testing:** Manual testing confirms tiles can be created, saved, loaded, and referenced in-game without missing tile errors.
    * **Labels:** `feature`, `overworld`, `tiles`, `editor`, `asset-pipeline`

* **[OVERWORLD-5] Add Overworld Music Per Map**
    * **Type:** Feature
    * **Priority:** High
    * **Description:** Add overworld music support with per-map soundtrack assignment so each map can define its own background music.
    * **Acceptance Criteria:**
        * Each map definition can reference a music track (by filename or ID).
        * Entering a map plays its assigned track and stops or fades out the previous map's track.
        * A default overworld track is used when a map does not specify one.
        * **Testing:** Manual testing confirms music switches correctly when changing maps and the default plays when no track is assigned.
    * **Labels:** `audio`, `overworld`, `feature`, `music`, `maps`

### Medium Priority

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

* **[POKE-23] Add Clipboard History + Persistent Favorite Paste Patterns**
    * **Type:** Feature
    * **Priority:** Medium
    * **Description:** Extend the existing copy/paste workflow in the pixel art editor with a clipboard history (multiple recently copied selections/patterns) and session-to-session persistent “favorites” for frequently reused patterns.
    * **Acceptance Criteria:**
        * Copy operations add the current selection/pattern to a bounded clipboard history (most-recent-first).
        * Users can browse/select an item from clipboard history to paste (via UI and/or hotkeys).
        * Users can mark clipboard items as favorites; favorites persist across app restarts.
        * Pasting a history/favorite item behaves like the current paste tool (preview + placement + cancel), without breaking existing copy/paste behavior.
    * **Testing:**
        * **Manual:** Confirms history ordering, favorite persistence, and correct paste placement across editor restarts.
        * **Automated (Unit/Integration):**
          - Clipboard history behavior: capacity limit, MRU ordering, and immutability (stored items don’t change when the canvas changes).
          - Favorites persistence: save → reload roundtrip preserves IDs/metadata/pixel data; missing/corrupt favorites file does not crash (loads empty with warning).
          - Paste computation: given a stored pattern + cursor position, computed paste bounds and applied pixels match expected, including clipping at canvas edges.
          - Undo/redo integration: pasting from history/favorite creates the intended undo granularity and restores exact pixels on undo/redo.
          - (If separable) Hotkey/UI selection: selecting next/prev clipboard item updates active paste source state without mutating history.
    * **Labels:** `editor`, `feature`, `ux`, `clipboard`, `pasting`, `persistence`

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

* **[TEST-4] Add Integration Test for Editor Startup**
    * **Type:** Task / Testing
    * **Priority:** Medium
    * **Description:** The current unit tests mock dependencies heavily and didn't catch an `AttributeError` related to `config.monsters` not being set during application startup via the root entry point script (`pixle_art_editor.py`). Create an integration test that attempts to launch the editor application (e.g., by running the entry script or using `python -m src.editor.pixle_art_editor`) and verifies that it initializes completely without crashing, including loading necessary data like monsters.
    * **Acceptance Criteria:**
        * An integration test exists that simulates application startup for the pixel art editor.
        * The test verifies that the editor initializes without critical errors (like the `AttributeError` for `config.monsters`).
        * The test uses minimal mocking, focusing on the integration of components during startup.
        * The test passes reliably.
    * **Labels:** `testing`, `integration-test`, `code-quality`, `editor`, `startup`

* **[REFACTOR-1] Inject Dependencies into Editor Class**
    * **Type:** Refactoring / Improvement
    * **Priority:** Medium
    * **Description:** The `Editor` class in `src/editor/pixle_art_editor.py` currently relies on globally loaded monster data (`config.monsters`) set by the entry point script. This makes the class harder to test in isolation and couples it to the startup sequence. Refactor the `Editor` class to accept dependencies like the loaded monster data via its constructor (`__init__`) instead of relying on global state. Update the entry point script (`pixle_art_editor.py`) to load the data and pass it to the `Editor` instance.
    * **Acceptance Criteria:**
        * `Editor.__init__` accepts necessary data (like loaded monster list) as arguments.
        * The `Editor` class uses the passed-in data instead of relying on `config.monsters`.
        * The root entry point script (`pixle_art_editor.py`) loads the data and passes it correctly during `Editor` instantiation.
        * Existing functionality remains unchanged.
        * Unit tests for `Editor` are potentially easier to write/maintain.
    * **Labels:** `refactoring`, `architecture`, `code-quality`, `maintainability`, `editor`, `dependency-injection`, `testing`

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

***
##### POKE-10 Sub-Tasks:

*   **[POKE-10.4] Refactor UI Drawing (`draw_ui`)**
    *   **Type:** Refactoring Task
    *   **Priority:** Medium
    *   **Description:** Simplify the `Editor.draw_ui` method by extracting UI drawing responsibilities. Move drawing logic for specific components (sprite editors view, background canvas view, palette, sliders, info text) into separate functions or methods, potentially within an `UIManager` or `EditorUI` class (using `ui_manager.py` or `editor_ui.py`). `Editor.draw_ui` should become primarily an orchestrator.
    *   **Acceptance Criteria:**
        *   The `Editor.draw_ui` method is significantly shorter and delegates drawing tasks.
        *   Drawing logic for distinct UI areas is encapsulated in separate functions/methods/classes.
        *   The overall UI appearance and layout remain unchanged.
        *   Relevant integration tests are **written and pass** to verify that `draw_ui` invokes sub-drawing routines correctly (may require surface mocking).
        *   Manual regression testing confirms the UI renders correctly in all modes.
    *   **Labels:** `refactoring`, `editor`, `code-quality`, `maintainability`, `architecture`, `ui`, `drawing`, `testing`

*   **[POKE-10.5] Refactor State Management**
    *   **Type:** Refactoring Task
    *   **Priority:** Medium
    *   **Description:** Centralize or better encapsulate the editor's state management. Aspects like `current_color`, `mode`, `edit_mode`, `brush_size`, `editor_zoom`, `view_offset`, undo/redo stacks, etc., could be grouped into a dedicated state object/class. Access to and modification of state should be managed through clearer interfaces.
    *   **Acceptance Criteria:**
        *   Editor state variables are grouped logically (e.g., in a dedicated state class).
        *   Access and modification of state are handled through well-defined methods or properties.
        *   The `Editor` class and other components access state through the new mechanism.
        *   All editor functionality relying on this state continues to work correctly.
        *   Relevant unit tests are **written and pass** for the state management logic, verifying state transitions and access.
        *   Manual regression testing confirms no state-related regressions.
    *   **Labels:** `refactoring`, `editor`, `code-quality`, `maintainability`, `architecture`, `state-management`, `testing`

*   **[POKE-10.6] Refactor File I/O and Dialogs**
    *   **Type:** Refactoring Task
    *   **Priority:** Medium-Low
    *   **Description:** Extract file loading/saving logic (monsters, sprites, backgrounds, reference images) and dialog interactions (including the Pygame-based dialog system and any remaining Tkinter calls) from the `Editor` class. This logic could reside in dedicated file I/O modules and a `DialogManager` (using `dialog_manager.py`).
    *   **Acceptance Criteria:**
        *   File loading/saving logic is moved out of the `Editor` class.
        *   Dialog presentation and handling logic are managed by a dedicated system (e.g., `DialogManager`).
        *   The `Editor` class calls the appropriate I/O or dialog functions.
        *   All file operations and dialog interactions work correctly.
        *   Relevant unit/integration tests are **written and pass** for file I/O functions (mocking FS access) and dialog management logic (testing state transitions/callbacks).
        *   Manual regression testing confirms all file and dialog operations work correctly.
    *   **Labels:** `refactoring`, `editor`, `code-quality`, `maintainability`, `architecture`, `file-io`, `dialogs`, `ui`, `testing`
    *   **Depends On:** Potentially `POKE-9`

---

## On Hold

* **[POKE-9] Fix Tkinter Initialization Conflicts**
    * **Type:** Bug / Task
    * **Priority:** Medium
    * **Description:** The pixel art editor (`pixle_art_editor.py`) relies on Python's built-in Tkinter library for the color picker and file dialogs (e.g., loading reference images), and removing it is currently blocked ([See ToDo](#on-hold)). However, initializing Tkinter (`tk.Tk()`) *after* Pygame (`pygame.init()`) can cause crashes on some systems (especially macOS) due to conflicts between SDL and Tkinter interacting with the windowing system (e.g., `-[SDLApplication macOSVersion]: unrecognized selector`). The goal is to fix this crash by ensuring Tkinter is initialized safely before Pygame, allowing its dialogs to function correctly.
    * **Acceptance Criteria:**
        * Tkinter initialization (`tk.Tk()`) does not crash the application when called.
        * Tkinter-dependent features (Color Picker, Load Ref Img) open their respective dialogs without crashing the main application.
        * The Tkinter root window remains hidden.
        * Pygame functionality is unaffected.
        * **Testing:** Unit tests confirm `_ensure_tkinter_root` (or equivalent logic) executes without error after Pygame init. Manual testing confirms Color Picker and Load Ref Img buttons successfully open dialogs without crashes.
    * **Labels:** `ui`, `ux`, `editor`, `dependencies`, `bug`, `blocked`, `macos`

---

## Done

* **[OVERWORLD-2] Add Map Editor Functionality (Design Doc Complete)**
    * **Type:** Feature
    * **Priority:** High
    * **Description:** Authored the map editor design and requirements in a dedicated design doc for future implementation.
    * **Outcome:** Design doc created at `docs/map-editor-design.md` covering UX/tools, data model, file format, validation, and runtime integration; ticket requirements relocated to the doc.
    * **Labels:** `feature`, `overworld`, `map`, `editor`, `tools`

* **[FEAT-REFIMG-PANZOOM] Implement Reference Image Panning and Scaling**
    * **Type:** Feature
    * **Priority:** Medium
    * **Description:** Currently, the reference image loaded in the monster editor (`[FEAT-REFIMG]`) is displayed at a fixed position and scale (aspect-fit). This can make it difficult to precisely align with the pixel grid, especially if the desired tracing area is small or off-center in the original image. Implement controls to allow the user to pan (move horizontally/vertically) and scale (zoom in/out) the reference image layer independently of the main pixel grid zoom/pan. This could involve dedicated UI buttons/sliders or keyboard modifiers + mouse interactions.
    * **Acceptance Criteria:**
        * Controls (UI elements or keyboard/mouse shortcuts) are available to pan the reference image horizontally and vertically.
        * Controls are available to scale the reference image up and down.
        * Panning and scaling operations affect only the reference image layer, not the pixel grid or other UI elements.
        * The transparency setting (`[FEAT-REFIMG]`) still functions correctly with the panned/scaled image.
        * The "Clear Ref Img" function resets any panning and scaling applied.
        * The editor remains performant even with panning/scaling applied.
        * **Testing:** Manual testing confirms panning and scaling controls work intuitively and independently of the main canvas controls.
        * **Testing:** Manual testing confirms transparency and clearing functions work correctly with the transformed image.
        * **Testing:** Unit/integration tests are *written and pass* for the panning/scaling logic, verifying correct transformation calculations and state updates (potentially mocking user input/GUI elements).
    * **Labels:** `feature`, `editor`, `ui`, `ux`, `reference-image`, `input`, `enhancement`, `testing`

*   **[POKE-10.3] Refactor Core Drawing/Tool Logic**
    *   **Type:** Refactoring Task
    *   **Priority:** Medium-High
    *   **Description:** Extract the logic for different editing tools (Draw, Erase, Fill, Paste) currently residing within the `Editor` class (e.g., in `_handle_canvas_click`, `flood_fill`, `apply_paste`) into separate classes or functions, potentially managed by a `ToolManager` using `tool_manager.py`. The `EventHandler` and `Editor` should delegate actions to the appropriate tool handler based on the current mode/tool.
    *   **Acceptance Criteria:**
        *   Logic for Draw, Erase, Fill, and Paste tools is encapsulated outside the main `Editor` class (e.g., in `tool_manager.py` or individual tool modules).
        *   The `Editor` class delegates canvas interactions (clicks/drags) to the active tool handler.
        *   The `EventHandler` correctly facilitates this delegation.
        *   All tools function correctly in both monster and background edit modes.
        *   Relevant unit/integration tests are **written and pass** for each extracted tool's logic, verifying correct pixel manipulation on a mock canvas or `SpriteEditor` frame.
        *   Manual regression testing confirms all tools work as expected.
    *   **Labels:** `refactoring`, `editor`, `code-quality`, `maintainability`, `architecture`, `tools`, `event-handling`, `testing`

*   **[POKE-10.1] Extract `SpriteEditor` Class**
    *   **Type:** Refactoring Task
    *   **Priority:** High
    *   **Description:** Move the `SpriteEditor` class definition from `pixle_art_editor.py` into its own dedicated module (e.g., `sprite_editor.py`). Update `pixle_art_editor.py` to import and use the class from the new module. Ensure all functionality related to sprite data handling (loading, saving, drawing pixels, getting grid positions) remains intact.
    *   **Acceptance Criteria:**
        *   The `SpriteEditor` class is defined in a separate file (e.g., `sprite_editor.py`).
        *   `pixle_art_editor.py` imports and instantiates `SpriteEditor` from the new module.
        *   All existing sprite editing functionality works as before.
        *   Relevant unit/integration tests are **written and pass** for the `SpriteEditor` class, verifying its core methods (e.g., `load_sprite`, `save_sprite`, `draw_pixel`, `get_grid_position`) in isolation or minimal integration.
        *   Manual regression testing confirms sprite editing remains fully functional.
    *   **Labels:** `refactoring`, `editor`, `code-quality`, `maintainability`, `architecture`, `sprite-editor`, `testing`

*   **[POKE-10.2] Extract `Palette` Class**
    *   **Type:** Refactoring Task
    *   **Priority:** High
    *   **Description:** Move the `Palette` class definition from `pixle_art_editor.py` into the `editor_ui.py` module. Update `pixle_art_editor.py` to import and use the class from its new location. Ensure color selection and palette scrolling functionality remain intact.
    *   **Acceptance Criteria:**
        *   The `Palette` class is defined in `editor_ui.py`.
        *   `pixle_art_editor.py` imports and instantiates `Palette` from `editor_ui.py`.
        *   Color selection using the palette works correctly.
        *   Palette scrolling functions as expected.
        *   Relevant unit/integration tests are **written and pass** for the `Palette` class, verifying its drawing and click handling logic (potentially mocking `editor.select_color`).
        *   Manual regression testing confirms palette interaction remains fully functional.
    *   **Labels:** `refactoring`, `editor`, `code-quality`, `maintainability`, `architecture`, `ui`, `palette`, `testing`

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

* **[POKE-22] Reorganize Project Folder Structure**
    * **Type:** Task / Improvement
    * **Priority:** Medium
    * **Description:** The current project structure has most Python modules (`pixle_art_editor.py`, `tool_manager.py`, `battle_simulator.py`, etc.) directly in the root directory. This can become hard to manage as the project grows. Reorganize the codebase into a more standard structure, likely involving a main `src/` directory with subdirectories for different components (e.g., `src/editor`, `src/battle`, `src/core`, `src/ui`, `src/utils`). Update all necessary imports and ensure the application and tests still run correctly after the reorganization.
    * **Acceptance Criteria:**
        * Python source files are moved into a logical directory structure (e.g., under `src/`).
        * All internal imports within the codebase are updated to reflect the new structure.
        * The main application entry points (e.g., `pixle_art_editor.py`, `battle_simulator.py`, potentially moved/adjusted) still launch the application correctly.
        * All unit tests pass after the reorganization (adjusting imports in tests as needed).
        * Directory structure is cleaner and easier to navigate.
    * **Labels:** `refactoring`, `architecture`, `code-quality`, `maintainability`

---
