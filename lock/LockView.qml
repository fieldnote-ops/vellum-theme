import QtQuick
import QtQuick.Effects
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui

Item {
  id: root

  property string backgroundPath: ""
  property int backgroundVersion: 0
  property bool fingerprintConfigured: false
  property bool authenticatingPassword: false
  property string failureMessage: ""
  property int failedAttempts: 0
  property bool inputEnabled: true
  property bool loadBackground: true
  property string passwordText: ""
  property bool syncingPasswordText: false
  property date now: new Date()
  property real entryProgress: 0
  property real shakeX: 0
  property real driftPhase: 0
  property bool sleepMonitorEnabled: true

  readonly property string placeholderText: "Enter Password"
  readonly property int fieldWidth: 381
  readonly property int fieldHeight: 67
  readonly property int outlineThickness: 3
  readonly property int fieldFontSize: Math.round(Style.font.heading * 1.125)
  readonly property int passwordDotFontSize: Math.round(Style.font.heading * 1.33)
  readonly property int passwordDotLetterSpacing: Math.round(Style.font.heading * 0.19)
  // Space to keep clear on each side of the field for the fingerprint icon
  // (icon width plus a gap) so the centered dots never run under it.
  readonly property real fingerprintReserve: fingerprintConfigured ? Math.round(fingerprintIcon.implicitWidth + 12) : 0
  // Shrink the dots to fit once the password outgrows the field, so every
  // keystroke stays visible — otherwise long passwords clip with no feedback.
  readonly property real passwordDotScale: dotMetrics.advanceWidth > 0
    ? Math.min(1, (passwordInput.width - 4) / dotMetrics.advanceWidth)
    : 1
  readonly property bool showPasswordCursor: inputEnabled && !authenticatingPassword && failureMessage.length === 0
  readonly property bool errorState: failureMessage.length > 0
  readonly property var inputBorderSpec: errorState
    ? Border.surfaceSpec("lock", "border-error", Commons.Color.lock.borderError, root.outlineThickness, "border-alpha")
    : Border.surfaceSpec("lock", "border-active", Commons.Color.lock.borderActive, root.outlineThickness, "border-alpha")

  signal submitPassword(string password)
  signal passwordTextEdited(string password)
  signal clearFailureRequested()
  signal wakeRequested()

  // Cache-busts the lock background by appending `?v=`. Adding a query
  // string keeps Image's loader happy while forcing it to reload when the
  // user picks a new background mid-session.
  function fileUrl(path) {
    if (!path) return ""
    var encoded = String(path).split("/").map(encodeURIComponent).join("/")
    return "file://" + encoded + "?v=" + backgroundVersion
  }

  function forcePasswordFocus() {
    passwordInput.forceActiveFocus()
  }

  function clearPassword() {
    passwordTextEdited("")
  }

  function syncPasswordText() {
    if (passwordInput.text === passwordText) return
    syncingPasswordText = true
    passwordInput.text = passwordText
    syncingPasswordText = false
  }

  function startEntry() {
    entryProgress = 0
    shakeX = 0
    driftPhase = 0
    wallpaperDrift.scale = 1.0
    now = new Date()
    entryAnimation.restart()
  }

  onPasswordTextChanged: syncPasswordText()
  onInputEnabledChanged: {
    if (inputEnabled) Qt.callLater(forcePasswordFocus)
  }
  onLoadBackgroundChanged: {
    if (loadBackground) startEntry()
    else {
      entryProgress = 0
      shakeX = 0
    }
  }
  onFailureMessageChanged: {
    if (failureMessage.length > 0) shakeAnimation.restart()
    else shakeX = 0
  }
  Component.onCompleted: {
    syncPasswordText()
    if (inputEnabled) Qt.callLater(forcePasswordFocus)
    if (loadBackground) startEntry()
  }

  Timer {
    interval: 1000
    running: true
    repeat: true
    onTriggered: root.now = new Date()
  }

  NumberAnimation {
    id: entryAnimation
    target: root
    property: "entryProgress"
    from: 0
    to: 1
    duration: 700
    easing.type: Easing.OutCubic
  }

  SequentialAnimation {
    id: shakeAnimation
    NumberAnimation { target: root; property: "shakeX"; to: 6; duration: 45; easing.type: Easing.OutQuad }
    NumberAnimation { target: root; property: "shakeX"; to: -6; duration: 45; easing.type: Easing.InOutQuad }
    NumberAnimation { target: root; property: "shakeX"; to: 4; duration: 45; easing.type: Easing.InOutQuad }
    NumberAnimation { target: root; property: "shakeX"; to: -4; duration: 45; easing.type: Easing.InOutQuad }
    NumberAnimation { target: root; property: "shakeX"; to: 0; duration: 60; easing.type: Easing.OutQuad }
  }

  // 12.5 fps drift: a 40 s breath, stepped slowly enough that the blur does
  // not have to re-render at the compositor's full frame rate.
  Timer {
    interval: 80
    running: root.loadBackground && root.entryProgress >= 1
    repeat: true
    onTriggered: {
      root.driftPhase = (root.driftPhase + 1 / 500) % 1
      wallpaperDrift.scale = 1.0 + 0.0125 * (1 - Math.cos(root.driftPhase * Math.PI * 2))
    }
  }

  // Replay one breath when logind reports that the machine has resumed.
  // dbus-monitor is only alive while the lock view is actually shown.
  Process {
    id: sleepMonitor
    command: ["dbus-monitor", "--system",
      "type='signal',sender='org.freedesktop.login1',interface='org.freedesktop.login1.Manager',member='PrepareForSleep'"]
    running: root.loadBackground && root.sleepMonitorEnabled
    stdout: SplitParser {
      onRead: function(line) {
        if (String(line).indexOf("boolean false") !== -1) root.startEntry()
      }
    }
    onExited: {
      if (root.loadBackground) {
        root.sleepMonitorEnabled = false
        sleepRestart.restart()
      }
    }
  }

  Timer {
    id: sleepRestart
    interval: 1500
    repeat: false
    onTriggered: root.sleepMonitorEnabled = true
  }

  // Measures the masked password at full size; passwordDotScale compares this
  // against the field width to decide how far the dots must shrink to fit.
  TextMetrics {
    id: dotMetrics
    font.family: Style.font.family
    font.pixelSize: root.passwordDotFontSize
    font.letterSpacing: root.passwordDotLetterSpacing
    text: "●".repeat(passwordInput.text.length)
  }

  Rectangle {
    anchors.fill: parent
    color: Commons.Color.background

    Item {
      id: wallpaperEntry
      anchors.fill: parent
      scale: 1.0 + 0.06 * (1 - root.entryProgress)

      Item {
        id: wallpaperDrift
        anchors.fill: parent
        scale: 1.0

        Image {
          id: wallpaper
          anchors.fill: parent
          source: root.loadBackground ? root.fileUrl(root.backgroundPath) : ""
          fillMode: Image.PreserveAspectCrop
          asynchronous: true
          cache: false
          sourceSize.width: width
          sourceSize.height: height
        }

        MultiEffect {
          anchors.fill: wallpaper
          source: wallpaper
          autoPaddingEnabled: false
          blurEnabled: root.loadBackground && wallpaper.status === Image.Ready
          blur: 1.0 - 0.45 * root.entryProgress
          blurMax: 64
          blurMultiplier: 0.9
          contrast: -0.08
        }
      }
    }

    Rectangle {
      anchors.fill: parent
      color: Util.alpha(Commons.Color.background, 0.16)
      opacity: root.entryProgress
    }

    MouseArea {
      anchors.fill: parent
      hoverEnabled: true
      onClicked: { root.wakeRequested(); root.forcePasswordFocus() }
      onPositionChanged: root.wakeRequested()
    }

    Column {
      id: clockBlock
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.bottom: inputField.top
      anchors.bottomMargin: 56
      spacing: 4
      opacity: root.entryProgress
      transform: Translate { y: (1 - root.entryProgress) * 14 }

      Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: Qt.formatTime(root.now, "HH:mm")
        color: Commons.Color.lock.text
        font.family: Style.font.family
        font.pixelSize: Math.round(Style.font.heading * 3.0)
        font.weight: Font.Light
      }

      Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: Qt.formatDate(root.now, "dddd, d MMMM")
        color: Commons.Color.lock.placeholder
        font.family: Style.font.family
        font.pixelSize: Math.round(Style.font.heading * 0.9)
      }

      Rectangle {
        width: 44
        height: 1
        anchors.horizontalCenter: parent.horizontalCenter
        color: Util.alpha(Commons.Color.accent, 0.55)
      }
    }

    BorderSurface {
      id: inputField
      width: root.fieldWidth
      height: root.fieldHeight
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.verticalCenter: parent.verticalCenter
      anchors.verticalCenterOffset: (1 - root.entryProgress) * 12
      opacity: root.entryProgress
      transform: Translate { x: root.shakeX }
      color: Commons.Color.lock.background
      borderSpec: root.inputBorderSpec
      radius: Style.cornerRadius
      clip: true

      TextInput {
        id: passwordInput
        anchors.fill: parent
        anchors.topMargin: inputField.borderTop
        // Reserve the fingerprint icon's width on both sides so the centered
        // dots stay symmetric and never slide under the icon as they grow.
        anchors.rightMargin: inputField.borderRight + 18 + root.fingerprintReserve
        anchors.bottomMargin: inputField.borderBottom
        anchors.leftMargin: inputField.borderLeft + 18 + root.fingerprintReserve
        verticalAlignment: TextInput.AlignVCenter
        horizontalAlignment: TextInput.AlignHCenter
        activeFocusOnPress: true
        clip: true
        enabled: root.inputEnabled && !root.authenticatingPassword
        readOnly: root.authenticatingPassword
        echoMode: TextInput.Password
        passwordCharacter: "\u25CF"
        passwordMaskDelay: 0
        color: Commons.Color.lock.text
        selectionColor: Commons.Color.lock.selection
        selectedTextColor: Commons.Color.lock.text
        font.family: Style.font.family
        font.pixelSize: text.length > 0 ? Math.max(1, Math.floor(root.passwordDotFontSize * root.passwordDotScale)) : root.fieldFontSize
        font.letterSpacing: text.length > 0 ? root.passwordDotLetterSpacing * root.passwordDotScale : 0
        cursorVisible: activeFocus && root.showPasswordCursor && text.length > 0
        cursorDelegate: Rectangle {
          width: 2
          color: Commons.Color.lock.text
          visible: passwordInput.cursorVisible
        }

        onTextChanged: {
          if (!root.syncingPasswordText) root.passwordTextEdited(text)
          if (text.length > 0) {
            root.wakeRequested()
          }
          if (text.length > 0 && root.failureMessage.length > 0) root.clearFailureRequested()
        }

        onAccepted: {
          var submitted = root.passwordText
          root.passwordTextEdited("")
          if (submitted.length > 0) root.submitPassword(submitted)
        }

        Keys.onPressed: function(event) {
          root.wakeRequested()
          if (event.key === Qt.Key_Escape || (event.modifiers & Qt.ControlModifier && event.key === Qt.Key_U)) {
            root.passwordTextEdited("")
            event.accepted = true
          }
        }
      }

      Text {
        textFormat: Text.PlainText
        anchors.fill: passwordInput
        text: root.authenticatingPassword ? "Checking…" : (root.failureMessage.length > 0 ? root.failureMessage : root.placeholderText)
        visible: passwordInput.text.length === 0
        color: root.authenticatingPassword ? Commons.Color.lock.text : (root.failureMessage.length > 0 ? Commons.Color.lock.textError : Commons.Color.lock.placeholder)
        font.family: Style.font.family
        font.pixelSize: root.fieldFontSize
        font.italic: !root.authenticatingPassword && root.failureMessage.length > 0
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
      }

      // Fingerprint hint pinned inside the field's right edge when a sensor is
      // enrolled, so the user knows they can touch to unlock instead of typing.
      // Matches hyprlock, which draws its fingerprint icon in the same spot.
      Text {
        id: fingerprintIcon
        objectName: "fingerprintIndicator"
        anchors.right: parent.right
        anchors.rightMargin: inputField.borderRight + 18
        anchors.verticalCenter: parent.verticalCenter
        visible: root.fingerprintConfigured
        SequentialAnimation on opacity {
          running: root.fingerprintConfigured
          loops: Animation.Infinite
          NumberAnimation { from: 0.55; to: 1.0; duration: 1300; easing.type: Easing.InOutSine }
          NumberAnimation { from: 1.0; to: 0.55; duration: 1300; easing.type: Easing.InOutSine }
        }
        text: "󰈷"
        color: Commons.Color.lock.placeholder
        font.family: Style.font.family
        font.pixelSize: Math.round(root.fieldFontSize * 1.1)
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
      }
    }
  }
}
