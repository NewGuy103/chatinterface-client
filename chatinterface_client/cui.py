from PySide6 import QtCore, QtGui, QtWidgets
from collections.abc import Callable


class UserFrame(QtWidgets.QFrame):
    clicked: QtCore.Signal = QtCore.Signal()

    def __init__(self, username: str) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        user_label: QtWidgets.QLabel = QtWidgets.QLabel(username)

        self.setLayout(layout)
        layout.addWidget(user_label)

        self.setFrameShape(QtWidgets.QFrame.Box)
        self.setFrameShadow(QtWidgets.QFrame.Plain)
        self.setLineWidth(2)
        self.setMidLineWidth(1)

        self.setObjectName('userFrame')
        self.setStyleSheet("""
            #userFrame {
                border: 2px solid grey;
                border-radius: 5px;
                /* background-color: white; */
            }
            #userFrame:hover {
                background-color: lightgrey
            }
        """)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class SavedLoginFrame(QtWidgets.QFrame):
    clicked: QtCore.Signal = QtCore.Signal()

    def __init__(self, host: str, user: str, checkbox: QtWidgets.QCheckBox) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)

        host_label: QtWidgets.QLabel = QtWidgets.QLabel(f"Host: {host}")
        user_label: QtWidgets.QLabel = QtWidgets.QLabel(f"User: {user}")

        self.setLayout(layout)
        layout.addWidget(host_label)
        layout.addWidget(user_label)

        layout.addWidget(checkbox)
        self.setFrameShape(QtWidgets.QFrame.Box)
        self.setFrameShadow(QtWidgets.QFrame.Plain)

        self.setLineWidth(2)
        self.setMidLineWidth(1)

        self.setObjectName('savedLoginFrame')
        self.setStyleSheet("""
            #savedLoginFrame {
                border: 2px solid grey;
                border-radius: 5px;
                /* background-color: white; */
            }
            #savedLoginFrame:hover {
                background-color: lightgrey
            }
        """)
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mouseMoveEvent(event)


class ContentScrollAreaWidget(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()

        layout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(layout)

        self.widget_list: list = []
    
    def add_message(self, user: str, message: str, send_date: str):
        if not isinstance(user, str):
            raise TypeError("user must be a string")
        
        if not isinstance(message, str):
            raise TypeError("message must be a string")
        
        if not isinstance(send_date, str):
            raise TypeError("send date must be a string")

        groupbox = QtWidgets.QGroupBox(f"User: {user}")
        layout = QtWidgets.QVBoxLayout()

        groupbox.setLayout(layout)
        label = QtWidgets.QLabel(message)

        label.setTextInteractionFlags(label.textInteractionFlags() | QtCore.Qt.TextSelectableByMouse)
        label.setCursor(QtCore.Qt.IBeamCursor)

        label.setWordWrap(True)
        layout.addWidget(label)

        label.setToolTip(f"Send Date: {send_date}")
        self.widget_list.append([groupbox, layout, label])

        self.layout().addWidget(groupbox)

    def update_message(self, message_index: int, message: str, append: bool = False):
        if not isinstance(message_index, int):
            raise TypeError("message index must be an int")

        if not isinstance(append, bool):
            raise TypeError("append must be a bool")

        if not isinstance(message, str):
            raise TypeError("message must be a string")

        if len(self.widget_list) - 1 < message_index:
            return print("holdon:", len(self.widget_list) - 1, message_index)
            # raise ValueError("message index out of range, consider adding messages first")

        label: QtWidgets.QLabel = self.widget_list[message_index][2]

        if append:
            original_text: str = label.text()
        else:
            original_text: str = ''

        label.setText(original_text + message)

    def delete_message(self):
        raise NotImplementedError("client has not yet implemented deletion")

    def clear_messages(self):
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                del item
        
        if getattr(self, 'widget_list', None):
            del self.widget_list

        self.widget_list = []


class UsersScrollAreaWidget(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()

        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)

        self.widget_dict: dict[str, QtWidgets.QFrame] = {}

    def add_user(self, username: str) -> UserFrame:
        frame: UserFrame = UserFrame(username)
        self.layout().addWidget(frame)

        if username in self.widget_dict:
            self.widget_dict[username].deleteLater()
            del self.widget_dict[username]

        self.widget_dict[username] = frame
        return frame


class SavedLoginsScrollAreaWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.selected_checkbox: QtWidgets.QCheckBox = None

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)

        self.setLayout(layout)

    def _set_selected(self, checkbox: QtWidgets.QCheckBox, callback: Callable):
        if self.selected_checkbox:
            self.selected_checkbox.setChecked(False)

        self.selected_checkbox = checkbox
        checkbox.setChecked(True)

        callback()

    def add_user(
            self, host: str, 
            user: str, 
            callback: Callable
    ) -> QtWidgets.QWidget:
        checkbox: QtWidgets.QCheckBox = QtWidgets.QCheckBox("Selected")
        checkbox.setEnabled(False)

        frame: SavedLoginFrame = SavedLoginFrame(host, user, checkbox)
        self.layout().addWidget(frame)

        frame.clicked.connect(lambda: self._set_selected(checkbox, callback))
        return frame


# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'window.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QLabel,
    QLineEdit, QMainWindow, QPlainTextEdit, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout,
    QWidget)


from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QFormLayout, QGridLayout, QLabel, QLineEdit,
    QPlainTextEdit, QSizePolicy, QVBoxLayout, QWidget)


class Ui_ComposeMessageDialog(object):
    def setupUi(self, ComposeMessageDialog):
        if not ComposeMessageDialog.objectName():
            ComposeMessageDialog.setObjectName(u"ComposeMessageDialog")
        ComposeMessageDialog.setWindowModality(Qt.WindowModality.WindowModal)
        ComposeMessageDialog.resize(400, 354)
        ComposeMessageDialog.setModal(True)
        self.verticalLayout = QVBoxLayout(ComposeMessageDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.mainWidget = QWidget(ComposeMessageDialog)
        self.mainWidget.setObjectName(u"mainWidget")
        self.formLayoutWidget = QWidget(self.mainWidget)
        self.formLayoutWidget.setObjectName(u"formLayoutWidget")
        self.formLayoutWidget.setGeometry(QRect(10, 10, 201, 21))
        self.nameFormLayout = QFormLayout(self.formLayoutWidget)
        self.nameFormLayout.setObjectName(u"nameFormLayout")
        self.nameFormLayout.setContentsMargins(0, 0, 0, 0)
        self.nameLabel = QLabel(self.formLayoutWidget)
        self.nameLabel.setObjectName(u"nameLabel")

        self.nameFormLayout.setWidget(0, QFormLayout.LabelRole, self.nameLabel)

        self.nameInput = QLineEdit(self.formLayoutWidget)
        self.nameInput.setObjectName(u"nameInput")
        self.nameInput.setMaxLength(20)

        self.nameFormLayout.setWidget(0, QFormLayout.FieldRole, self.nameInput)

        self.gridLayoutWidget = QWidget(self.mainWidget)
        self.gridLayoutWidget.setObjectName(u"gridLayoutWidget")
        self.gridLayoutWidget.setGeometry(QRect(10, 40, 361, 251))
        self.messageGridLayout = QGridLayout(self.gridLayoutWidget)
        self.messageGridLayout.setObjectName(u"messageGridLayout")
        self.messageGridLayout.setContentsMargins(0, 0, 0, 0)
        self.messageLabel = QLabel(self.gridLayoutWidget)
        self.messageLabel.setObjectName(u"messageLabel")

        self.messageGridLayout.addWidget(self.messageLabel, 0, 0, 1, 1)

        self.messageInput = QPlainTextEdit(self.gridLayoutWidget)
        self.messageInput.setObjectName(u"messageInput")

        self.messageGridLayout.addWidget(self.messageInput, 1, 0, 1, 1)


        self.verticalLayout.addWidget(self.mainWidget)

        self.mainButtonBox = QDialogButtonBox(ComposeMessageDialog)
        self.mainButtonBox.setObjectName(u"mainButtonBox")
        self.mainButtonBox.setOrientation(Qt.Orientation.Horizontal)
        self.mainButtonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        self.mainButtonBox.setCenterButtons(False)

        self.verticalLayout.addWidget(self.mainButtonBox)


        self.retranslateUi(ComposeMessageDialog)
        self.mainButtonBox.accepted.connect(ComposeMessageDialog.accept)
        self.mainButtonBox.rejected.connect(ComposeMessageDialog.reject)

        QMetaObject.connectSlotsByName(ComposeMessageDialog)
    # setupUi

    def retranslateUi(self, ComposeMessageDialog):
        ComposeMessageDialog.setWindowTitle(QCoreApplication.translate("ComposeMessageDialog", u"Compose new message", None))
        self.nameLabel.setText(QCoreApplication.translate("ComposeMessageDialog", u"Name: ", None))
#if QT_CONFIG(tooltip)
        self.nameInput.setToolTip(QCoreApplication.translate("ComposeMessageDialog", u"Enter recipient username. Example: johndoe123", None))
#endif // QT_CONFIG(tooltip)
        self.nameInput.setPlaceholderText(QCoreApplication.translate("ComposeMessageDialog", u"johndoe", None))
        self.messageLabel.setText(QCoreApplication.translate("ComposeMessageDialog", u"Message:", None))
        self.messageInput.setPlaceholderText(QCoreApplication.translate("ComposeMessageDialog", u"Enter message here...", None))
    # retranslateUi


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1366, 696)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.mainStackedWidget = QStackedWidget(self.centralwidget)
        self.mainStackedWidget.setObjectName(u"mainStackedWidget")
        self.loginPage = QWidget()
        self.loginPage.setObjectName(u"loginPage")
        self.gridLayout_2 = QGridLayout(self.loginPage)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.loginPage_widget = QWidget(self.loginPage)
        self.loginPage_widget.setObjectName(u"loginPage_widget")
        self.loginPage_frame = QFrame(self.loginPage_widget)
        self.loginPage_frame.setObjectName(u"loginPage_frame")
        self.loginPage_frame.setGeometry(QRect(470, 130, 381, 350))
        self.loginPage_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.loginPage_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.loginPage_usernameInput = QLineEdit(self.loginPage_frame)
        self.loginPage_usernameInput.setObjectName(u"loginPage_usernameInput")
        self.loginPage_usernameInput.setGeometry(QRect(20, 70, 340, 50))
        font = QFont()
        font.setPointSize(12)
        self.loginPage_usernameInput.setFont(font)
        self.loginPage_usernameInput.setMaxLength(20)
        self.loginPage_usernameInput.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.loginPage_label = QLabel(self.loginPage_frame)
        self.loginPage_label.setObjectName(u"loginPage_label")
        self.loginPage_label.setGeometry(QRect(20, 10, 341, 51))
        font1 = QFont()
        font1.setFamilies([u"Ubuntu"])
        font1.setPointSize(24)
        font1.setBold(True)
        self.loginPage_label.setFont(font1)
        self.loginPage_passwordInput = QLineEdit(self.loginPage_frame)
        self.loginPage_passwordInput.setObjectName(u"loginPage_passwordInput")
        self.loginPage_passwordInput.setGeometry(QRect(20, 140, 340, 50))
        self.loginPage_passwordInput.setFont(font)
        self.loginPage_passwordInput.setMaxLength(32767)
        self.loginPage_passwordInput.setEchoMode(QLineEdit.EchoMode.Password)
        self.loginPage_passwordInput.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.loginPage_serverHostInput = QLineEdit(self.loginPage_frame)
        self.loginPage_serverHostInput.setObjectName(u"loginPage_serverHostInput")
        self.loginPage_serverHostInput.setGeometry(QRect(20, 210, 340, 50))
        self.loginPage_serverHostInput.setFont(font)
        self.loginPage_serverHostInput.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.loginPage_loginButton = QPushButton(self.loginPage_frame)
        self.loginPage_loginButton.setObjectName(u"loginPage_loginButton")
        self.loginPage_loginButton.setGeometry(QRect(20, 280, 340, 50))
        font2 = QFont()
        font2.setPointSize(14)
        self.loginPage_loginButton.setFont(font2)

        self.gridLayout_2.addWidget(self.loginPage_widget, 1, 0, 1, 1)

        self.mainStackedWidget.addWidget(self.loginPage)
        self.savedLoginsPage = QWidget()
        self.savedLoginsPage.setObjectName(u"savedLoginsPage")
        self.verticalLayout_2 = QVBoxLayout(self.savedLoginsPage)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.savedLogins_widget = QWidget(self.savedLoginsPage)
        self.savedLogins_widget.setObjectName(u"savedLogins_widget")
        self.widget = QWidget(self.savedLogins_widget)
        self.widget.setObjectName(u"widget")
        self.widget.setGeometry(QRect(620, 250, 120, 80))
        self.savedLogins_frame = QFrame(self.savedLogins_widget)
        self.savedLogins_frame.setObjectName(u"savedLogins_frame")
        self.savedLogins_frame.setGeometry(QRect(470, 100, 381, 441))
        self.savedLogins_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.savedLogins_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.savedLogins_label = QLabel(self.savedLogins_frame)
        self.savedLogins_label.setObjectName(u"savedLogins_label")
        self.savedLogins_label.setGeometry(QRect(20, 10, 341, 51))
        font3 = QFont()
        font3.setFamilies([u"Ubuntu"])
        font3.setPointSize(16)
        font3.setBold(False)
        self.savedLogins_label.setFont(font3)
        self.savedLogins_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.savedLogins_label.setWordWrap(True)
        self.savedLogins_loginButton = QPushButton(self.savedLogins_frame)
        self.savedLogins_loginButton.setObjectName(u"savedLogins_loginButton")
        self.savedLogins_loginButton.setGeometry(QRect(20, 380, 340, 50))
        self.savedLogins_loginButton.setFont(font2)
        self.savedLogins_scrollArea = QScrollArea(self.savedLogins_frame)
        self.savedLogins_scrollArea.setObjectName(u"savedLogins_scrollArea")
        self.savedLogins_scrollArea.setGeometry(QRect(20, 60, 340, 300))
        self.savedLogins_scrollArea.setWidgetResizable(True)
        self.savedLoginsScrollAreaWidget = SavedLoginsScrollAreaWidget()
        self.savedLoginsScrollAreaWidget.setObjectName(u"savedLoginsScrollAreaWidget")
        self.savedLoginsScrollAreaWidget.setGeometry(QRect(0, 0, 338, 298))
        self.savedLogins_scrollArea.setWidget(self.savedLoginsScrollAreaWidget)

        self.verticalLayout_2.addWidget(self.savedLogins_widget)

        self.mainStackedWidget.addWidget(self.savedLoginsPage)
        self.chatPage = QWidget()
        self.chatPage.setObjectName(u"chatPage")
        self.gridLayout = QGridLayout(self.chatPage)
        self.gridLayout.setObjectName(u"gridLayout")
        self.chatPage_widget = QWidget(self.chatPage)
        self.chatPage_widget.setObjectName(u"chatPage_widget")
        self.chatPage_messageFrame = QFrame(self.chatPage_widget)
        self.chatPage_messageFrame.setObjectName(u"chatPage_messageFrame")
        self.chatPage_messageFrame.setGeometry(QRect(270, 10, 1051, 580))
        self.chatPage_messageFrame.setFrameShape(QFrame.Shape.StyledPanel)
        self.chatPage_messageFrame.setFrameShadow(QFrame.Shadow.Raised)
        self.chatPage_recipientFrame = QFrame(self.chatPage_messageFrame)
        self.chatPage_recipientFrame.setObjectName(u"chatPage_recipientFrame")
        self.chatPage_recipientFrame.setGeometry(QRect(10, 20, 1030, 40))
        self.chatPage_recipientFrame.setFrameShape(QFrame.Shape.StyledPanel)
        self.chatPage_recipientFrame.setFrameShadow(QFrame.Shadow.Raised)
        self.chatPage_recipientName = QLabel(self.chatPage_recipientFrame)
        self.chatPage_recipientName.setObjectName(u"chatPage_recipientName")
        self.chatPage_recipientName.setGeometry(QRect(10, 9, 181, 20))
        self.chatPage_recipientName.setFont(font2)
        self.chatPage_contentScrollArea = QScrollArea(self.chatPage_messageFrame)
        self.chatPage_contentScrollArea.setObjectName(u"chatPage_contentScrollArea")
        self.chatPage_contentScrollArea.setGeometry(QRect(10, 70, 1031, 501))
        self.chatPage_contentScrollArea.setWidgetResizable(True)
        self.contentScrollAreaWidget = ContentScrollAreaWidget()
        self.contentScrollAreaWidget.setObjectName(u"contentScrollAreaWidget")
        self.contentScrollAreaWidget.setGeometry(QRect(0, 0, 1029, 499))
        self.chatPage_contentScrollArea.setWidget(self.contentScrollAreaWidget)
        self.chatPage_userFrame = QFrame(self.chatPage_widget)
        self.chatPage_userFrame.setObjectName(u"chatPage_userFrame")
        self.chatPage_userFrame.setGeometry(QRect(10, 10, 250, 60))
        self.chatPage_userFrame.setFrameShape(QFrame.Shape.StyledPanel)
        self.chatPage_userFrame.setFrameShadow(QFrame.Shadow.Raised)
        self.chatPage_menuButton = QPushButton(self.chatPage_userFrame)
        self.chatPage_menuButton.setObjectName(u"chatPage_menuButton")
        self.chatPage_menuButton.setGeometry(QRect(10, 20, 50, 23))
        self.chatPage_usernameLabel = QLabel(self.chatPage_userFrame)
        self.chatPage_usernameLabel.setObjectName(u"chatPage_usernameLabel")
        self.chatPage_usernameLabel.setGeometry(QRect(70, 22, 171, 21))
        font4 = QFont()
        font4.setPointSize(11)
        font4.setBold(True)
        self.chatPage_usernameLabel.setFont(font4)
        self.chatPage_usernameLabel.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
        self.chatPage_usernameLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.chatPage_inputFrame = QFrame(self.chatPage_widget)
        self.chatPage_inputFrame.setObjectName(u"chatPage_inputFrame")
        self.chatPage_inputFrame.setGeometry(QRect(270, 600, 1050, 50))
        self.chatPage_inputFrame.setFrameShape(QFrame.Shape.StyledPanel)
        self.chatPage_inputFrame.setFrameShadow(QFrame.Shadow.Raised)
        self.chatPage_messageInput = QPlainTextEdit(self.chatPage_inputFrame)
        self.chatPage_messageInput.setObjectName(u"chatPage_messageInput")
        self.chatPage_messageInput.setGeometry(QRect(10, 10, 920, 30))
        self.chatPage_sendButton = QPushButton(self.chatPage_inputFrame)
        self.chatPage_sendButton.setObjectName(u"chatPage_sendButton")
        self.chatPage_sendButton.setGeometry(QRect(940, 10, 100, 30))
        self.chatPage_usersScrollArea = QScrollArea(self.chatPage_widget)
        self.chatPage_usersScrollArea.setObjectName(u"chatPage_usersScrollArea")
        self.chatPage_usersScrollArea.setGeometry(QRect(10, 130, 250, 520))
        self.chatPage_usersScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chatPage_usersScrollArea.setWidgetResizable(True)
        self.usersScrollAreaWidget = UsersScrollAreaWidget()
        self.usersScrollAreaWidget.setObjectName(u"usersScrollAreaWidget")
        self.usersScrollAreaWidget.setGeometry(QRect(0, 0, 248, 518))
        self.chatPage_usersScrollArea.setWidget(self.usersScrollAreaWidget)
        self.chatPage_composeMessageFrame = QFrame(self.chatPage_widget)
        self.chatPage_composeMessageFrame.setObjectName(u"chatPage_composeMessageFrame")
        self.chatPage_composeMessageFrame.setGeometry(QRect(10, 80, 250, 40))
        self.chatPage_composeMessageFrame.setFrameShape(QFrame.Shape.StyledPanel)
        self.chatPage_composeMessageFrame.setFrameShadow(QFrame.Shadow.Raised)
        self.chatPage_composeMessageButton = QPushButton(self.chatPage_composeMessageFrame)
        self.chatPage_composeMessageButton.setObjectName(u"chatPage_composeMessageButton")
        self.chatPage_composeMessageButton.setGeometry(QRect(10, 10, 230, 23))

        self.gridLayout.addWidget(self.chatPage_widget, 0, 0, 1, 1)

        self.mainStackedWidget.addWidget(self.chatPage)

        self.verticalLayout.addWidget(self.mainStackedWidget)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.mainStackedWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"chatInterface", None))
        self.loginPage_usernameInput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Enter username", None))
        self.loginPage_label.setText(QCoreApplication.translate("MainWindow", u"Login to chatInterface", None))
        self.loginPage_passwordInput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Enter password", None))
        self.loginPage_serverHostInput.setText("")
        self.loginPage_serverHostInput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Enter server IP/hostname", None))
        self.loginPage_loginButton.setText(QCoreApplication.translate("MainWindow", u"Login", None))
        self.savedLogins_label.setText(QCoreApplication.translate("MainWindow", u"Choose a saved login below:", None))
        self.savedLogins_loginButton.setText(QCoreApplication.translate("MainWindow", u"Use this login", None))
        self.chatPage_recipientName.setText(QCoreApplication.translate("MainWindow", u"{recipient username}", None))
        self.chatPage_menuButton.setText(QCoreApplication.translate("MainWindow", u"Menu", None))
        self.chatPage_usernameLabel.setText(QCoreApplication.translate("MainWindow", u"{current username}", None))
        self.chatPage_sendButton.setText(QCoreApplication.translate("MainWindow", u"Send Message", None))
        self.chatPage_composeMessageButton.setText(QCoreApplication.translate("MainWindow", u"Compose new message", None))
    # retranslateUi


