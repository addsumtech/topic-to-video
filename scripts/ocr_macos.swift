// macOS Vision text recognition for scripts/screen_text.py — prints JSON lines with boxes as image fractions
// (top-left origin). Compiled once per source hash into ~/.cache/slides-to-video/.
import AppKit
import Foundation
import Vision

guard CommandLine.arguments.count > 1,
      let img = NSImage(contentsOfFile: CommandLine.arguments[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
  FileHandle.standardError.write("cannot read the image\n".data(using: .utf8)!)
  exit(2)
}
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = false
req.recognitionLanguages = ["zh-Hans", "en-US"]
do {
  try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
} catch {
  FileHandle.standardError.write("vision failed: \(error)\n".data(using: .utf8)!)
  exit(3)
}
var out: [[String: Any]] = []
for obs in req.results ?? [] {
  guard let cand = obs.topCandidates(1).first else { continue }
  let b = obs.boundingBox
  out.append(["text": cand.string, "box": [b.minX, 1 - b.maxY, b.maxX, 1 - b.minY]])
}
let data = try! JSONSerialization.data(withJSONObject: out, options: [])
FileHandle.standardOutput.write(data)
