import traceback
import sys
import asyncio

import uuid
import keyring
import httpx

from PySide6.QtCore import QObject
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox
)
from qasync import QEventLoop, asyncSlot
from urllib.parse import urlparse

from .interfaces.route_clients import TokenRouteClient, ChatsRouteClient
from .interfaces.ws import WSClient
from .cui import Ui_MainWindow


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


class LoginPage(QObject):
    def __init__(self, parent: MainWindow) -> None:
        super().__init__()
        self.ui: Ui_MainWindow = parent.ui

        self.ui.loginPage_loginButton.clicked.connect(self.start_login)

        creds: tuple = self.get_saved_login()
        if creds:
            asyncio.ensure_future(self.proceed_to_login(creds[0], creds[1]))
            return

    def get_saved_login(self):
        saved_host: str = keyring.get_password("chatinterface.client.local", 'saved_host')
        if not saved_host:
            return
        
        saved_token: str = keyring.get_password("chatinterface.client.token", saved_host)
        if not saved_token:
            return

        return (saved_host, saved_token)

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

        keyring.set_password("chatinterface.client.local", 'saved_host', host_without_path)
        keyring.set_password("chatinterface.client.token", host_without_path, token)

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
        asyncio.ensure_future(self._on_chat_change())

    async def initClientList(self):
        def set_current_chat(username):
            self.current_chat = username

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
            frame.mousePressEvent = lambda _, name=name: set_current_chat(name)

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

    @asyncSlot()
    async def _on_chat_change(self):
        prev_chat: str = ""
        text_area = self.ui.chatPage_textArea

        while self._running:
            await asyncio.sleep(0)

            if not self.current_chat:
                continue

            if prev_chat == self.current_chat:
                continue  # current chat is the same

            prev_chat: str = self.current_chat
            message_list: list[tuple[str, str, str]] = self.messages[prev_chat]

            self.ui.chatPage_recipientName.setText(prev_chat)
            text_area.clear()

            for chat_tuple in message_list:
                current_name: str = chat_tuple[0]
                chat_text: str = chat_tuple[1]

                text_area.add_message(current_name, chat_text)

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

        self.ui.mainStackedWidget.setCurrentIndex(1)

        # self.ui.chatPage_menuButton.clicked.connect(self.dialog_ChatDashboardMenu.show)
        self.ui.chatPage_sendButton.clicked.connect(self.send_chat_message)

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
        self.text_area = parent.ui.chatPage_textArea

    async def message_received(self, data: dict):
        sender: str = data.get('sender')
        message: str = data.get('data')

        timestamp: str = data.get('timestamp')
        if sender not in self.messages:
            self.parent.messages[sender] = []

        self.parent.messages[sender].append([sender, message, timestamp])
        if not self.current_chat:
            return

        self.text_area.add_message(sender, message, timestamp)

    async def message_completed(self, data: dict):
        message_id: str = data.get('id')
        recipient: str = data.get('recipient')

        stored_msg: str = self.parent.uncompleted_messages[message_id]
        created_msg: list = [recipient, stored_msg]

        self.parent.messages[recipient].append(created_msg)
        del self.parent.uncompleted_messages[message_id]

        self.text_area.add_message(self.parent.username, stored_msg)

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
