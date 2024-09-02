import traceback
import sys
import asyncio

import uuid
import httpx

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox,
    QDialog, QWidget
)
from qasync import QEventLoop, asyncSlot
from urllib.parse import urlparse

from .interfaces.route_clients import TokenRouteClient, ChatsRouteClient
from .interfaces.ws import WSClient
from .interfaces.loginstore import KeyringManager
from .cui import Ui_MainWindow, Ui_ComposeMessageDialog


def make_msgbox(text: str, extra_text: str = '', icon: QMessageBox.Icon | None = None) -> None:
    if not icon:
        icon = QMessageBox.Icon.Information
    
    msgbox: QMessageBox = QMessageBox()
    msgbox.setWindowTitle('chatInterface')

    msgbox.setText(text)
    msgbox.setInformativeText(extra_text)

    msgbox.setIcon(icon)
    msgbox.exec()

    msgbox.deleteLater()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        # move this to the setup with checking http/websocket host here...
        # also maybe remove the ws host box, replace with a server url, we set it to /ws/chat only
        self.ui: Ui_MainWindow = Ui_MainWindow()
        self.app: QApplication = QApplication.instance()

        self.ui.setupUi(self)
        self.show()

        self.loginPage: LoginPage = LoginPage(self)


class ComposeMessageDialog(QDialog):
    accepted: Signal = Signal(str, str)

    def __init__(
            self, parent: QWidget | None = None, 
            f: Qt.WindowType = Qt.WindowType.Dialog
    ) -> None:
        super().__init__(parent, f)
        self.ui: Ui_ComposeMessageDialog = Ui_ComposeMessageDialog()

        self.ui.setupUi(self)
    
    def accept(self):
        name: str = self.ui.nameInput.text()
        message: str = self.ui.messageInput.toPlainText()

        if not name or not message:
            make_msgbox(
                "Missing name or message input",
                "Enter the required fields and try again",
                icon=QMessageBox.Icon.Warning
            )
            return

        self.accepted.emit(name, message)
        super().accept()


class LoginPage(QObject):
    def __init__(self, parent: MainWindow) -> None:
        super().__init__()

        self.ui: Ui_MainWindow = parent.ui
        self.ui.loginPage_loginButton.clicked.connect(self.start_login)

        self.keyring_manager: KeyringManager = KeyringManager()
        asyncio.ensure_future(self.initCore())

    async def initCore(self):
        await self.keyring_manager.setup()
        users: list | str = await self.keyring_manager.show_users()

        if len(users) == 1:
            first_user: tuple = users[0]
            token: str = await self.keyring_manager.get_password(first_user[0], first_user[1])

            await self.proceed_to_login(first_user[0], token)
            return
        elif len(users) > 1:
            await self.choose_login(users)
            return

    @asyncSlot()
    async def start_login(self):
        host: str = self.ui.loginPage_serverHostInput.text()
        if not host:
            make_msgbox(
                "Missing server URL",
                "Enter a server URL (like https://example.com)",
                icon=QMessageBox.Icon.Warning
            )
            return

        username: str = self.ui.loginPage_usernameInput.text()
        password: str = self.ui.loginPage_passwordInput.text()

        if not username or not password:
            make_msgbox(
                "Missing username or password",
                "Enter credentials and try again",
                icon=QMessageBox.Icon.Warning
            )
            return

        parsed_host = urlparse(host)
        httpx_client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=20, headers={'Accept': 'application/json'}
        )
        host_without_path: str = f"{parsed_host.scheme}://{parsed_host.netloc}"

        token_client: TokenRouteClient = TokenRouteClient(host_without_path, httpx_client)
        token: dict | str = await token_client.create_token(username, password)

        if isinstance(token, tuple):
            err_code: str = token[0]
            exc: Exception = token[1]

            exc_tb: str = ''.join(traceback.format_exception_only(exc))
            match err_code:
                case "INVALID_URL":
                    make_msgbox(
                        "Invalid server URL",
                        "Enter a valid server URL.",
                        icon=QMessageBox.Icon.Warning
                    )
                case "NETWORK_ERROR":
                    make_msgbox(
                        "Token creation failed with network error",
                        f"Check your internet or try again later.\nTraceback:\n\n{exc_tb}",
                        icon=QMessageBox.Icon.Warning
                    )
                case "HTTP_STATUS_ERROR":
                    make_msgbox(
                        "Server returned HTTP error status",
                        f"Traceback:\n\n{exc_tb}",
                        icon=QMessageBox.Icon.Warning
                    )
                case "INVALID_JSON":
                    make_msgbox(
                        "Server returned invalid JSON",
                        f"Traceback:\n\n{exc_tb}",
                        icon=QMessageBox.Icon.Warning
                    )
                case "HTTP_ERROR":
                    make_msgbox(
                        "Other HTTP error occured when creating token",
                        f"Traceback:\n\n{exc_tb}",
                        icon=QMessageBox.Icon.Warning
                    )
                case "ERROR":
                    make_msgbox(
                        "Unexpected error occured when creating token"
                        f"Traceback:\n\n{exc_tb}",
                        icon=QMessageBox.Icon.Critical
                    )
            return

        await self.keyring_manager.set_password(host_without_path, username, token)
        await self.proceed_to_login(host, token)

    async def proceed_to_login(self, host: str, token: str):
        parsed_host = urlparse(host)
        match parsed_host.scheme:
            case "http":
                ws_scheme: str = 'ws'
            case "https":
                ws_scheme: str = 'wss'
            case _:
                make_msgbox(
                    "URL is not http/https",
                    "Enter a valid server URL (like https://example.com)",
                    icon=QMessageBox.Icon.Warning
                )
                return

        ws_host: str = f"{ws_scheme}://{parsed_host.netloc}/ws/chat"
        self.dashboardWindow = DashboardPage(host, ws_host, token, self.ui)

    @asyncSlot()
    async def choose_login(self, users: list[tuple]):
        saved_logins = self.ui.savedLoginsScrollAreaWidget

        chosen_user: str = ''
        chosen_host: str = ''

        login_clicked: bool = False

        def set_chosen_user(user: str, host: str):
            nonlocal chosen_user, chosen_host
            chosen_user = user
            chosen_host = host

        def set_login_clicked():
            nonlocal login_clicked, chosen_user, chosen_host
            if not chosen_host and not chosen_user:
                make_msgbox(
                    "No saved login selected",
                    "Select a saved login before logging in",
                    icon=QMessageBox.Icon.Warning
                )
                return

            login_clicked = True

        self.ui.mainStackedWidget.setCurrentIndex(1)
        self.ui.savedLogins_loginButton.clicked.connect(set_login_clicked)

        for user_tuple in users:
            host: str = user_tuple[0]
            user: str = user_tuple[1]

            saved_logins.add_user(
                host, user, 
                lambda user=user, host=host: set_chosen_user(user, host)
            )

        while True:  # make this use events next time
            await asyncio.sleep(0.05)
            if not chosen_user:
                continue

            if login_clicked:
                break

        token: str = await self.keyring_manager.get_password(chosen_host, chosen_user)
        await self.proceed_to_login(chosen_host, token)


class DashboardPage(QObject):
    def __init__(self, http_host: str, ws_host: str, token: str, ui: Ui_MainWindow) -> None:
        super().__init__()
        headers: dict = {
            'Accept': 'application/json',
            'Authorization': token
        }
        http_client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=20, headers=headers
        )

        self.__token: str = token
        self._running: bool = True
        self.username: str = ''

        self.current_chat: str = ''
        self.messages: dict[str, list] = {}

        self.uncompleted_messages: dict = {}
        self.chat_client: ChatsRouteClient = ChatsRouteClient(http_host, http_client)

        self.token_client: TokenRouteClient = TokenRouteClient(http_host, http_client)
        self.ws_client: WSClient = WSClient(ws_host)

        self.ui: Ui_MainWindow = ui
        self.callbacks: WebSocketCallbacks = WebSocketCallbacks(self)

        self.dialog_ComposeMessage: ComposeMessageDialog = ComposeMessageDialog(
            self.ui.chatPage_widget, Qt.WindowType.Dialog
        )
        # self.dialog_ChatDashboardMenu: Dialog_ChatDashboardMenu = Dialog_ChatDashboardMenu(self)

        asyncio.ensure_future(self.initCore())
        self.initUI()

    @asyncSlot()
    async def initCore(self):
        await self.ws_client.setup(self.__token)

        self.ws_client.add_handler("message.received", self.callbacks.message_received)
        self.ws_client.add_handler("message.completed", self.callbacks.message_completed)

        self.ws_client.add_handler("error.closed", self.callbacks.socket_closed)
        if not await self.initClientList():
            return

        self.ui.chatPage_usernameLabel.setText(self.username)

    async def initClientList(self):
        loop = asyncio.get_event_loop()

        user_widget = self.ui.usersScrollAreaWidget
        session_info: tuple | dict = await self.token_client.show_token_info(self.__token)
        if isinstance(session_info, tuple):  # [data, error]
            make_msgbox(
                "Fetching session info failed", 
                f"Could not retrieve session info due to error:\n{str(session_info[1])}",
                icon=QMessageBox.Icon.Warning
            )
            return

        self.username: str = session_info['username']
        recipients: set[str] | tuple = await self.chat_client.get_contacts()

        if isinstance(recipients, tuple):
            make_msgbox(
                "Fetching previous contacts failed", 
                f"Could not retrieve contacts due to error:\n{str(recipients[1])}",
                icon=QMessageBox.Icon.Warning
            )
            return

        failed_fetches: set = set()
        complete_fetches: set = set()

        for name in recipients:
            messages: list[tuple[str, str, str]] | tuple = await self.chat_client.get_messages(
                name, 100
            )
            if isinstance(messages, tuple):
                failed_fetches.add(name)
                continue

            frame = user_widget.add_user(name)
            frame.clicked.connect(lambda name=name: loop.create_task(self._change_contact(name)))

            self.messages[name] = list(reversed(messages))  # most recent will show up first
            complete_fetches.add(name)

        if failed_fetches:
            if not complete_fetches:
                make_msgbox(
                    "Failed to fetch message list of all contacts", 
                    "Request errors can be found in the log file.",
                    icon=QMessageBox.Icon.Critical
                )
            else:
                make_msgbox(
                    "Failed to fetch message list of some contacts", 
                    "Some contacts will be unavailable.\nRequest errors can be found in the log file."
                    f"\nFetch failed for contacts: {', '.join(failed_fetches)}",
                    icon=QMessageBox.Icon.Warning
                )

        return True

    async def _change_contact(self, username: str):
        content_area = self.ui.contentScrollAreaWidget

        if username == self.current_chat:
            return  # current chat is the same

        self.current_chat: str = username
        message_list: list[tuple[str, str, str]] = self.messages[username]

        self.ui.chatPage_recipientName.setText(username)
        content_area.clear_messages()

        for chat_tuple in message_list:
            current_name: str = chat_tuple[0]
            chat_text: str = chat_tuple[1]

            send_date: str = chat_tuple[2]
            content_area.add_message(current_name, chat_text, send_date)

        await asyncio.sleep(0.05)
        scroll_bar = self.ui.chatPage_contentScrollArea.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def initUI(self):
        def switch_theme():
            theme = self.ui.themeSlider.value()
            if theme == 1:
                self.setStyleSheet("""
                    QObject {
                        background-color: #2b2b2b; 
                        color: #ffffff;
                    }
                    #chatFrame {
                        border: 2px solid #666666;
                        border-radius: 5px;
                    }
                """)
            else:
                self.setStyleSheet("""
                    QObject {
                        background-color: #EFEFEF; 
                        color: #000000;    
                    }
                    #chatFrame {
                        border: 2px solid #b8b8b8;
                        border-radius: 5px;
                    }
                """)

        # commented until i can create the menu to enforce light/dark mode
        # switch_theme()
        # self.ui.themeSlider.valueChanged.connect(switch_theme)
        # self.ui.themeSlider.setCursor(Qt.PointingHandCursor)

        self.ui.mainStackedWidget.setCurrentIndex(2)
        self.ui.chatPage_composeMessageButton.clicked.connect(self.dialog_ComposeMessage.show)

        # self.ui.chatPage_menuButton.clicked.connect(self.dialog_ChatDashboardMenu.show)
        self.ui.chatPage_sendButton.clicked.connect(self.send_chat_message)

        self.dialog_ComposeMessage.accepted.connect(self.add_new_contact)

    @asyncSlot(str, str)
    async def add_new_contact(self, name: str, message: str):
        user_exists: tuple | bool = await self.chat_client.check_user_exists(name)
        if isinstance(user_exists, tuple):
            make_msgbox(
                "Could not compose new message",
                f"Failed due to error: {str(user_exists[1])}",
                icon=QMessageBox.Icon.Critical
            )
            return

        if not user_exists:
            make_msgbox(
                "Could not compose new message",
                "User does not exist",
                icon=QMessageBox.Icon.Warning
            )
            return

        self.ui.usersScrollAreaWidget.add_user(name)
        message_id: str = str(uuid.uuid4())
        data: dict = {
            "recipient": name,
            "data": message,
            "id": message_id
        }

        self.messages[name] = []
        self.uncompleted_messages[message_id] = message

        await self.ws_client.send_message("message.send", data)

    @asyncSlot()
    async def send_chat_message(self):
        if not self.current_chat:
            return

        message: str = self.ui.chatPage_messageInput.toPlainText()
        if not message:
            return

        message_id: str = str(uuid.uuid4())
        data: dict = {
            "recipient": self.current_chat,
            "data": message,
            "id": message_id
        }

        self.uncompleted_messages[message_id] = message
        await self.ws_client.send_message("message.send", data)

        self.ui.chatPage_messageInput.clear()


class WebSocketCallbacks:
    def __init__(self, parent: DashboardPage) -> None:
        self.parent: DashboardPage = parent
        self.ui: Ui_MainWindow = parent.ui

        self.ws_client: WSClient = parent.ws_client
        self.content_area = parent.ui.contentScrollAreaWidget

    async def message_received(self, data: dict):
        sender: str = data.get('sender')
        message: str = data.get('data')

        timestamp: str = data.get('timestamp')
        if sender not in self.parent.messages:
            self.parent.messages[sender] = []

        self.parent.messages[sender].append([sender, message, timestamp])
        if not self.parent.current_chat:
            return

        self.content_area.add_message(sender, message, timestamp)

    async def message_completed(self, data: dict):
        message_id: str = data.get('id')
        recipient: str = data.get('recipient')
        timestamp: str = data.get('timestamp')

        stored_msg: str = self.parent.uncompleted_messages[message_id]
        created_msg: list = [recipient, stored_msg, timestamp]

        self.parent.messages[recipient].append(created_msg)
        del self.parent.uncompleted_messages[message_id]

        if self.parent.current_chat == recipient:
            self.content_area.add_message(self.parent.username, stored_msg, timestamp)

    async def socket_closed(self, data: dict):
        delay_seconds: int = 4
        for attempt in range(1, 5):
            reconnect_result: tuple[int | str, Exception | None] = await self.ws_client.reconnect()
            if reconnect_result[0] == 0:
                await self.parent.initClientList()
                return
            
            await asyncio.sleep(delay_seconds * (2**attempt))
        
        make_msgbox(
            "Reconnect failed",
            "Failed to reconnect to server after 4 times",
            icon=QMessageBox.Icon.Critical
        )


def main():
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = MainWindow()  # noqa
    with loop:
        loop.run_forever()


if __name__ == '__main__':
    main()
