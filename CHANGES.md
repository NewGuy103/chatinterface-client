# Implement message composing properly

**Version:** v0.1.0

**Date:** 10/22/2024

## Additions

**`interfaces/route_clients.py`**:

* Added `ChatsRouteClient.compose_new_message()` for message composing.

**`cui.py`**:

* Moved `ComposeMessageDialog` to this file for message compose dialog.

**`config.py`**:

* Added `RuntimeState` to simplify keeping runtime state.

## Changes

**`interfaces/route_clients.py`**:

* Changed `ChatsRouteClient.check_user_exists()` endpoint route to use a `_` instead of a `-`.

**`loginstore.py`**:

* `KeyringManager.show_users()` now returns `None` instead of `NO_USERS` when there are no saved logins.

**`gui.py`**:

* Moved `ComposeMessageDialog` to `cui.py`.
* Changed variable references to make the app reference a `RuntimeState`.

## Misc

* Will implement message editing and deletion.
