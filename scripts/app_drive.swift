// app_drive — the hand on the mouse and keyboard for scripts/app_record.py: the REAL cursor, moved the way a person
// moves it (eased, at a human pace), so a tutorial's recording is the app as it really behaves, cursor and all.
//
//   app_drive move X Y [MS]        glide to the global point (top-left origin, points) over MS ms (eased in-out)
//   app_drive click X Y [MS] [N] [MODS]  glide there, press and release N times (2: a double-click), holding MODS
//                                  ("shift", "cmd+shift"): shift-click extends a table selection
//   app_drive drag X1 Y1 X2 Y2 [MS]  glide to the start, press, glide to the end with the button held, release
//   app_drive scroll LINES          turn the wheel under the cursor (positive: toward the top of the page)
//   app_drive type TEXT [CPS]      type TEXT at CPS characters a second (a person types ~6-12)
//   app_drive key COMBO            one key with modifiers: "cmd+a", "return", "shift+tab", "cmd+shift+4"
//   app_drive pos                  print where the cursor is
// Every command prints one line: "ok <x> <y>" (the cursor after it). Needs Accessibility for the terminal; without it
// macOS drops the events silently, so app_record.py checks that the cursor really arrived.
import CoreGraphics
import Foundation

// Events carry the HID system's state: with a nil source a drag is seen as a click at its end (Numbers ignored
// every synthetic drag-select and object move, 2026-11-25); with it, drags select and move as a hand's do.
let SRC = CGEventSource(stateID: .hidSystemState)
func now() -> CGPoint { CGEvent(source: nil)!.location }
func post(_ e: CGEvent?) { e?.post(tap: .cghidEventTap) }
func ease(_ u: Double) -> Double { u < 0.5 ? 4 * u * u * u : 1 - pow(-2 * u + 2, 3) / 2 }

func glide(to p: CGPoint, ms: Double, button: CGMouseButton? = nil) {
  let a = now(), steps = max(1, Int(ms / 1000 * 60))
  for i in 1...steps {
    let u = ease(Double(i) / Double(steps))
    let q = CGPoint(x: a.x + (p.x - a.x) * u, y: a.y + (p.y - a.y) * u)
    let type: CGEventType = button == nil ? .mouseMoved : .leftMouseDragged
    let e = CGEvent(mouseEventSource: SRC, mouseType: type, mouseCursorPosition: q, mouseButton: .left)
    if button != nil { e?.setIntegerValueField(.mouseEventClickState, value: 1) }   // a drag without it is a click (Numbers)
    post(e)
    usleep(useconds_t(1_000_000 / 60))
  }
}

func press(_ p: CGPoint, down: Bool, count: Int64 = 1, flags: CGEventFlags = []) {
  let e = CGEvent(mouseEventSource: SRC, mouseType: down ? .leftMouseDown : .leftMouseUp, mouseCursorPosition: p,
                  mouseButton: .left)
  e?.setIntegerValueField(.mouseEventClickState, value: count)   // 2 on the second press = a double-click
  if !flags.isEmpty { e?.flags = flags }                         // shift-click: a range in a table
  post(e)
}

func holdMods(_ f: CGEventFlags, down: Bool) {
  let keys: [(CGEventFlags, CGKeyCode)] = [(.maskShift, 56), (.maskCommand, 55), (.maskAlternate, 58), (.maskControl, 59)]
  var held = down ? CGEventFlags() : f
  for (flag, code) in keys where f.contains(flag) {
    if down { held.insert(flag) } else { held.remove(flag) }
    let e = CGEvent(keyboardEventSource: SRC, virtualKey: code, keyDown: down)
    e?.flags = held
    post(e)
    usleep(30_000)
  }
}

func modFlags(_ s: String) -> CGEventFlags {
  var f = CGEventFlags()
  for part in s.lowercased().split(separator: "+") {
    switch part {
    case "shift": f.insert(.maskShift)
    case "cmd": f.insert(.maskCommand)
    case "alt", "option": f.insert(.maskAlternate)
    case "ctrl": f.insert(.maskControl)
    default: fail("unknown modifier \(part)")
    }
  }
  return f
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
    let e = CGEvent(keyboardEventSource: SRC, virtualKey: c, keyDown: down)
    e?.flags = flags
    post(e)
    usleep(20_000)
  }
  return true
}

func type(_ text: String, cps: Double) {
  for ch in text {
    for down in [true, false] {
      let e = CGEvent(keyboardEventSource: SRC, virtualKey: 0, keyDown: down)
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
case "click": guard a.count >= 4 else { fail("click X Y [MS] [N] [MODS]") }
  let p = CGPoint(x: num(2, 0), y: num(3, 0)), n = max(1, min(3, Int64(num(5, 1))))
  let fl = a.count > 6 && !a[6].isEmpty ? modFlags(a[6]) : CGEventFlags()
  glide(to: p, ms: num(4, 600)); usleep(80_000)
  holdMods(fl, down: true)        // the keys really held: an app may read the keyboard's state, not the click's flags
  for i in 1...n {
    press(p, down: true, count: i, flags: fl); usleep(70_000); press(p, down: false, count: i, flags: fl)
    if i < n { usleep(90_000) }   // within the system's double-click interval
  }
  holdMods(fl, down: false)
case "drag": guard a.count >= 6 else { fail("drag X1 Y1 X2 Y2 [MS]") }
  let p = CGPoint(x: num(2, 0), y: num(3, 0)), q = CGPoint(x: num(4, 0), y: num(5, 0))
  glide(to: p, ms: 500); press(p, down: true); usleep(120_000)
  glide(to: q, ms: num(6, 800), button: .left); usleep(80_000); press(q, down: false)
case "scroll": guard a.count >= 3 else { fail("scroll LINES (positive: toward the top)") }
  let n = Int(num(2, 0))
  for _ in 0..<abs(n) {           // a line at a time, as a wheel turns, under the cursor
    post(CGEvent(scrollWheelEvent2Source: SRC, units: .line, wheelCount: 1, wheel1: n > 0 ? 1 : -1, wheel2: 0, wheel3: 0))
    usleep(25_000)
  }
case "type": guard a.count >= 3 else { fail("type TEXT [CPS]") }
  type(a[2], cps: num(3, 10))
case "key": guard a.count >= 3, key(a[2]) else { fail("key COMBO: unknown key in \(a.count >= 3 ? a[2] : "")") }
default: fail("unknown command \(a[1])")
}
let p = now()
print("ok \(Int(p.x.rounded())) \(Int(p.y.rounded()))")
