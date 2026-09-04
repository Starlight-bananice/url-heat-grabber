// Apply the standard rounded app-icon silhouette when exporting a generated tile.
// The generated symbol and colors are retained; the outer matte is not packaged.
import AppKit
import Foundation

let args = CommandLine.arguments
if args.count != 3 { fatalError("Usage: package_icon.swift SOURCE OUTPUT_PNG") }
guard let source = NSImage(contentsOfFile: args[1]) else { fatalError("Cannot read source icon") }
let side = 1024
let bounds = NSRect(x: 0, y: 0, width: side, height: side)
guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: side, pixelsHigh: side,
    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
    colorSpaceName: .deviceRGB, bytesPerRow: side * 4, bitsPerPixel: 32),
    let context = NSGraphicsContext(bitmapImageRep: bitmap) else { fatalError("Cannot make icon bitmap") }
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = context
context.imageInterpolation = .high
NSColor.clear.setFill()
bounds.fill(using: .copy)
// A regular export silhouette stays within the generated tile's colored edge.
let tile = NSRect(x: 59, y: 61, width: 906, height: 900)
NSBezierPath(roundedRect: tile, xRadius: 228, yRadius: 228).addClip()
source.draw(in: bounds, from: .zero, operation: .sourceOver, fraction: 1)
context.flushGraphics()
NSGraphicsContext.restoreGraphicsState()
guard let data = bitmap.representation(using: .png, properties: [:]) else { fatalError("PNG encoding failed") }
try data.write(to: URL(fileURLWithPath: args[2]))
print("Exported 1024 px application icon with transparent outer corners.")
