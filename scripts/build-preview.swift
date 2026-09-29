#!/usr/bin/env swift

import AppKit
import Foundation

guard CommandLine.arguments.count == 3 else {
    FileHandle.standardError.write(
        Data("Usage: build-preview.swift <atlas.webp> <preview.png>\n".utf8)
    )
    exit(1)
}

let sourceURL = URL(fileURLWithPath: CommandLine.arguments[1])
let destinationURL = URL(fileURLWithPath: CommandLine.arguments[2])

guard let data = try? Data(contentsOf: sourceURL),
      let image = NSImage(data: data),
      let atlas = image.cgImage(
          forProposedRect: nil,
          context: nil,
          hints: nil
      ),
      atlas.width >= 192,
      atlas.height >= 208,
      let frame = atlas.cropping(
          to: CGRect(x: 0, y: 0, width: 192, height: 208)
      ) else {
    FileHandle.standardError.write(
        Data("Could not decode the first atlas frame.\n".utf8)
    )
    exit(1)
}

let bitmap = NSBitmapImageRep(cgImage: frame)
guard let png = bitmap.representation(using: .png, properties: [:]) else {
    FileHandle.standardError.write(Data("Could not encode the preview.\n".utf8))
    exit(1)
}

try FileManager.default.createDirectory(
    at: destinationURL.deletingLastPathComponent(),
    withIntermediateDirectories: true
)
try png.write(to: destinationURL, options: .atomic)
