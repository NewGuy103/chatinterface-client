# Make code use PySide6 signal/slots

**Version:** v0.1.0

**Date:** 09/02/2024

## Additions

**`pyside6_ui/newmessage.ui`**:

* Dialog to compose a new message.

**`cui.py`**:

* Added `UserFrame`, `SavedLoginFrame` to allow usage for signal/slots.
* Added `SavedLoginsScrollAreaWidget` to display saved logins easily.
* Added `Ui_ComposeMessageDialog` created from `pyside6-uic`.
* Added saved logins page to display saved logins.

**`__main__.py`**:

* Entrypoint to run module as a script.

**`gui.py`**:

* Added support for composing a message to a user through `ComposeMessageDialog`.
* Added partial support for multiple users. (Creating a new saved login while logged in has not been implemented yet)
* Added `DashboardPage.add_new_contact()` for `ComposeMessageDialog`.

**`loginstore.py`**:

* Created to allow multi-login support for the client.
* This uses `keyring` to store the tokens, `sqlite3` to map the uuids to the tokens,
  and uses a wrapper to turn the methods async.

**`route_clients.py`**:

* Added `ChatsRouteClient.check_user_exists()` to check if a username exists on the server.

## Changes

**`cui.py`**:

* Delete `SimpleChatTextBrowser` since we are now using `ContentScrollAreaWidget` to display messages.
* `UsersScrollAreaWidget` now uses `UserFrame` to make click events easier.
* Changed `UsersScrollAreaWidget` to be a QFrame.

**`gui.py`**:

* `DashboardPage._on_chat_change()` has been replaced with `_change_contact()` and is triggered by a signal.
* Changed `DashboardPage` to switch the widget page to index 2 (the chat page).
* Fixed `WebSocketCallbacks` methods not referencing parent variables.

## Misc

* Planning to make the GUI use PySide6's signal/slots for events.
* Planning to use a shared data object for `WebSocketCallbacks`.
