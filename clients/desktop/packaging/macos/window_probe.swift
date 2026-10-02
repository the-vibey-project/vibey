// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The windows one process has on screen, as the window server reports them: one line per
// window, `layer x y width height`. scripts/macos_app_bundle.py's smoke test compiles this
// and runs it against the app it launched. CoreGraphics reports a window's owner and bounds
// without the screen-recording permission a screenshot would need.
//
//   window_probe <pid>
import CoreGraphics
import Foundation

guard CommandLine.arguments.count == 2, let pid = Int(CommandLine.arguments[1]) else {
    FileHandle.standardError.write("usage: window_probe <pid>\n".data(using: .utf8)!)
    exit(2)
}
let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as? [[String: Any]] ?? []
for window in windows where (window[kCGWindowOwnerPID as String] as? Int) == pid {
    let layer = window[kCGWindowLayer as String] as? Int ?? -1
    let bounds = window[kCGWindowBounds as String] as? [String: Any] ?? [:]
    let x = bounds["X"] as? Double ?? 0, y = bounds["Y"] as? Double ?? 0
    let width = bounds["Width"] as? Double ?? 0, height = bounds["Height"] as? Double ?? 0
    print("\(layer) \(Int(x)) \(Int(y)) \(Int(width)) \(Int(height))")
}
