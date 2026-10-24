import QtQuick
import QtQuick.Shapes
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import qs.Commons as Commons

// Vellum Ambient
//
// A deliberately small overlay above the wallpaper and below normal windows.
// Two ripples inside the dawn sun: a warm clay primary and a faint verdigris
// echo. The animation is procedural: no frame cache, no video decoder, and it
// stays crisp at fractional scale.
//
// It only appears on the 0-dawn background, pauses on idle, lock, and while a
// fullscreen window is active. The surface masks out all input.
Item {
  id: root

  readonly property string home: Quickshell.env("HOME")
  readonly property string stateHome: home + "/.local/state"
  readonly property string backgroundLink: stateHome + "/omarchy/current/background"
  readonly property string dawnBackground: "0-dawn"

  // The sun in 0-dawn is at (2260, 520) of a 2880x1920 image.
  readonly property real anchorX: 2260 / 2880
  readonly property real anchorY: 520 / 1920

  property string backgroundPath: ""
  property bool locked: false
  property real phase: 0

  readonly property bool isDawn: backgroundPath.length > 0
    && new RegExp("(^|/)" + dawnBackground + "\\.(jpe?g|png|webp|gif)$", "i").test(backgroundPath)

  readonly property bool fullscreenActive: ToplevelManager.activeToplevel
    ? ToplevelManager.activeToplevel.fullscreen
    : false

  readonly property bool paused: locked || idleMonitor.isIdle || fullscreenActive
  readonly property bool running: isDawn && !paused

  // A very slow breath under the ripples, peaking between their births. It is
  // deliberately below the threshold of "an effect": the sun gains depth, not
  // a visible halo.
  readonly property real glowAlpha: 0.018 + 0.026
    * (0.5 + 0.5 * Math.cos((phase - 0.29) * Math.PI * 2))

  function refreshBackground() {
    if (!readlinkProc.running) readlinkProc.running = true
  }

  function refreshLock() {
    if (!lockProc.running) lockProc.running = true
  }

  Component.onCompleted: {
    refreshBackground()
    refreshLock()
  }

  // Fast enough to follow a theme/background change without a visible lag.
  Timer {
    interval: 2000
    running: true
    repeat: true
    onTriggered: {
      root.refreshBackground()
      root.refreshLock()
    }
  }

  // 12.5 fps over a 12 s loop. The eased radius starts at ~1.8 px/frame and
  // settles, so this rate reads as a slow exhale rather than a stepped spinner.
  Timer {
    interval: 80
    running: root.running
    repeat: true
    onTriggered: root.phase = (root.phase + 1 / 150) % 1
  }

  Process {
    id: readlinkProc
    command: ["readlink", "-f", root.backgroundLink]
    stdout: StdioCollector {
      onStreamFinished: root.backgroundPath = String(text || "").trim()
    }
  }

  Process {
    id: lockProc
    command: ["omarchy-shell", "lock", "isLocked"]
    stdout: StdioCollector {
      onStreamFinished: root.locked = String(text || "").trim() === "true"
    }
  }

  IdleMonitor {
    id: idleMonitor
    timeout: 60
    respectInhibitors: true
    enabled: true
  }

  IpcHandler {
    target: "vellum.ambient"

    function status(): string {
      return JSON.stringify({
        background: root.backgroundPath,
        dawn: root.isDawn,
        paused: root.paused,
        locked: root.locked,
        idle: idleMonitor.isIdle,
        fullscreen: root.fullscreenActive,
        phase: root.phase
      })
    }
  }

  Variants {
    model: Quickshell.screens

    PanelWindow {
      id: panel
      required property var modelData
      screen: modelData
      anchors { top: true; left: true; right: true; bottom: true }
      color: "transparent"
      WlrLayershell.namespace: "vellum-ambient"
      WlrLayershell.layer: WlrLayer.Bottom
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
      exclusionMode: ExclusionMode.Ignore
      // Visual-only surface: never intercept the background's double-click.
      mask: Region {}

      Item {
        id: rings
        width: 420
        height: 420
        visible: root.isDawn

        // Vellum's backgrounds are generated at 2880x1920. The plugin is
        // deliberately tied to 0-dawn, so the anchor can use that source size
        // directly instead of decoding the wallpaper a second time.
        readonly property real srcWidth: 2880
        readonly property real srcHeight: 1920
        readonly property real cover: Math.max(panel.width / srcWidth, panel.height / srcHeight)
        readonly property real shownWidth: srcWidth * cover
        readonly property real shownHeight: srcHeight * cover
        readonly property real originX: (panel.width - shownWidth) / 2
        readonly property real originY: (panel.height - shownHeight) / 2

        x: Math.round(originX + root.anchorX * shownWidth - width / 2)
        y: Math.round(originY + root.anchorY * shownHeight - height / 2)

        // The glow is a stationary radial wash; only its alpha moves.
        Shape {
          anchors.fill: parent
          antialiasing: true
          // The gradient itself is static; animating its Item opacity is both
          // cheaper and reliably repainted by the scene graph.
          opacity: root.glowAlpha / 0.044

          ShapePath {
            strokeColor: "transparent"
            fillGradient: RadialGradient {
              centerX: 210
              centerY: 210
              centerRadius: 200
              focalX: 210
              focalY: 210
              focalRadius: 0

              GradientStop {
                position: 0
                color: Qt.rgba(1.0, 0.965, 0.855, 0.044)
              }
              GradientStop {
                position: 0.55
                color: Qt.rgba(1.0, 0.965, 0.855, 0.0154)
              }
              GradientStop { position: 1; color: "transparent" }
            }

            startX: 0
            startY: 0
            PathLine { x: 420; y: 0 }
            PathLine { x: 420; y: 420 }
            PathLine { x: 0; y: 420 }
            PathLine { x: 0; y: 0 }
          }
        }

        Repeater {
          model: 2

          Item {
            id: ripple
            anchors.fill: parent
            transformOrigin: Item.Center

            // Unequal spacing (0 and 0.58) avoids the metronomic three-ring
            // canon: births alternate at 6.96 s and 5.04 s.
            readonly property real progress: (root.phase + (index === 0 ? 0 : 0.58)) % 1
            readonly property real peak: index === 0 ? 0.14 : 0.06

            // Fast initial expansion, long settle. A linear scale reads as a
            // loading spinner; this reads as something spreading through paper.
            readonly property real eased: 1 - Math.pow(1 - progress, 2.2)
            readonly property color ink: index === 0 ? "#9c4f17" : Commons.Color.accent
            readonly property real mainWidth: index === 0 ? 1.2 : 0.9

            // Transform properties rather than path geometry: the scene graph
            // repaints these reliably every tick.
            scale: 0.27 + 0.73 * eased
            rotation: (index === 0 ? 0 : 120) + 26 * progress

            // Fast attack, long decay: it appears in ~1.4 s and takes the rest
            // of the 12 s loop to disappear.
            opacity: peak * Math.min(1, progress / 0.12)
              * Math.pow(1 - progress, 1.6)

            Shape {
              anchors.fill: parent
              antialiasing: true

              // A wider, very faint duplicate gives the ink a soft edge
              // without a blur pass: the vector line stops looking sharper
              // than the grain in the wallpaper.
              ShapePath {
                strokeColor: Util.alpha(ripple.ink, 0.24)
                strokeWidth: ripple.mainWidth * 2.8
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap

                PathAngleArc {
                  centerX: 210
                  centerY: 210
                  radiusX: 170
                  radiusY: 170
                  startAngle: index === 0 ? -50 : 112
                  sweepAngle: index === 0 ? 300 : 258
                }
              }

              ShapePath {
                // Warm primary, cool echo. The sun is warm, so clay leads.
                strokeColor: ripple.ink
                strokeWidth: ripple.mainWidth
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap

                PathAngleArc {
                  centerX: 210
                  centerY: 210
                  radiusX: 170
                  radiusY: 170
                  startAngle: index === 0 ? -50 : 112
                  sweepAngle: index === 0 ? 300 : 258
                }
              }
            }
          }
        }
      }
    }
  }
}
