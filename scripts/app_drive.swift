// app_drive — the hand on the mouse and keyboard for scripts/app_record.py: the REAL cursor, moved the way a person
// moves it (eased, at a human pace), so a tutorial's recording is the app as it really behaves, cursor and all.
//
//   app_drive move X Y [MS]        glide to the global point (top-left origin, points) over MS ms (eased in-out)
//   app_drive click X Y [MS]       glide there, then press and release
//   app_drive drag X1 Y1 X2 Y2 [MS]  glide to the start, press, glide to the end with the button held, release
//   app_drive type TEXT [CPS]      type TEXT at CPS characters a second (a person types ~6-12)
//   app_drive key COMBO            one key with modifiers: "cmd+a", "return", "shift+tab", "cmd+shift+4"
//   app_drive pos                  print where the cursor is
// Every command prints one line: "ok <x> <y>" (the cursor after it). Needs Accessibility for the terminal; without it
// macOS drops the events silently, so app_record.py checks that the cursor really arrived.
import CoreGraphics
import Foundation

func now() -> CGPoint { CGEvent(source: nil)!.location }
func post(_ e: CGEvent?) { e?.post(tap: .cghidEventTap) }
func ease(_ u: Double) -> Double { u < 0.5 ? 4 * u * u * u : 1 - pow(-2 * u + 2, 3) / 2 }

func glide(to p: CGPoint, ms: Double, button: CGMouseButton? = nil) {
  let a = now(), steps = max(1, Int(ms / 1000 * 60))
  for i in 1...steps {
    let u = ease(Double(i) / Double(steps))
    let q = CGPoint(x: a.x + (p.x - a.x) * u, y: a.y + (p.y - a.y) * u)
    let type: CGEventType = button == nil ? .mouseMoved : .leftMouseDragged
    post(CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: q, mouseButton: .left))
    usleep(useconds_t(1_000_000 / 60))
  }
}

func press(_ p: CGPoint, down: Bool) {
  post(CGEvent(mouseEventSource: nil, mouseType: down ? .leftMouseDown : .leftMouseUp, mouseCursorPosition: p,
               mouseButton: .left))
}

let KEYS: [String: CGKeyCode] = [
  "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12, "w": 13, "e": 14,
  "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "9": 25, "7": 26, "8": 28, "0": 29,
  "o": 31, "u": 32, "i": 34, "p": 35, "l": 37, "j": 38, "k": 40, "n": 45, "m": 46, "return": 36, "tab": 48,
  "space": 49, "delete": 51, "escape": 53, "left": 123, "right": 124, "down": 125, "up": 126,
]

func key(_ combo: String) -> Bool {
  var flags = CGEventFlags()
  var code: CGKeyCode? = nil
  for part in combo.lowercased().split(separator: "+").map(String.init) {
    switch part {
    case "cmd": flags.insert(.maskCommand)
    case "shift": flags.insert(.maskShift)
    case "alt", "option": flags.insert(.maskAlternate)
    case "ctrl": flags.insert(.maskControl)
    default: code = KEYS[part]
    }
  }
  guard let c = code else { return false }
  for down in [true, false] {
    let e = CGEvent(keyboardEventSource: nil, virtualKey: c, keyDown: down)
    e?.flags = flags
    post(e)
    usleep(20_000)
  }
  return true
}

func type(_ text: String, cps: Double) {
  for ch in text {
    for down in [true, false] {
      let e = CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: down)
      var u = Array(String(ch).utf16)
      e?.keyboardSetUnicodeString(stringLength: u.count, unicodeString: &u)
      post(e)
    }
    usleep(useconds_t(1_000_000 / max(1, cps)))
  }
}

let a = CommandLine.arguments
func num(_ i: Int, _ d: Double) -> Double { a.count > i ? Double(a[i]) ?? d : d }
func fail(_ m: String) -> Never { FileHandle.standardError.write((m + "\n").data(using: .utf8)!); exit(2) }
guard a.count >= 2 else { fail("usage: app_drive move|click|drag|type|key|pos ...") }
switch a[1] {
case "pos": break
case "move": guard a.count >= 4 else { fail("move X Y [MS]") }
  glide(to: CGPoint(x: num(2, 0), y: num(3, 0)), ms: num(4, 600))
case "click": guard a.count >= 4 else { fail("click X Y [MS]") }
  let p = CGPoint(x: num(2, 0), y: num(3, 0))
  glide(to: p, ms: num(4, 600)); usleep(80_000); press(p, down: true); usleep(70_000); press(p, down: false)
case "drag": guard a.count >= 6 else { fail("drag X1 Y1 X2 Y2 [MS]") }
  let p = CGPoint(x: num(2, 0), y: num(3, 0)), q = CGPoint(x: num(4, 0), y: num(5, 0))
  glide(to: p, ms: 500); press(p, down: true); usleep(120_000)
  glide(to: q, ms: num(6, 800), button: .left); usleep(80_000); press(q, down: false)
case "type": guard a.count >= 3 else { fail("type TEXT [CPS]") }
  type(a[2], cps: num(3, 10))
case "key": guard a.count >= 3, key(a[2]) else { fail("key COMBO: unknown key in \(a.count >= 3 ? a[2] : "")") }
default: fail("unknown command \(a[1])")
}
let p = now()
print("ok \(Int(p.x.rounded())) \(Int(p.y.rounded()))")
