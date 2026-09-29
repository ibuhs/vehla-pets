#!/usr/bin/env swift

import CryptoKit
import Foundation

enum SigningError: Error, CustomStringConvertible {
    case usage
    case missingPrivateKey
    case invalidPrivateKey
    case unreadableCatalog

    var description: String {
        switch self {
        case .usage:
            return "Usage: catalog-signing.swift public-key | sign <catalog>"
        case .missingPrivateKey:
            return "VEHLA_PUBLISHER_PRIVATE_KEY is required."
        case .invalidPrivateKey:
            return "VEHLA_PUBLISHER_PRIVATE_KEY must be a base64 Ed25519 private key."
        case .unreadableCatalog:
            return "The catalog could not be read."
        }
    }
}

func privateKey() throws -> Curve25519.Signing.PrivateKey {
    guard let encoded = ProcessInfo.processInfo.environment[
        "VEHLA_PUBLISHER_PRIVATE_KEY"
    ] else {
        throw SigningError.missingPrivateKey
    }
    guard let data = Data(base64Encoded: encoded),
          let key = try? Curve25519.Signing.PrivateKey(
            rawRepresentation: data
          ) else {
        throw SigningError.invalidPrivateKey
    }
    return key
}

do {
    guard CommandLine.arguments.count >= 2 else {
        throw SigningError.usage
    }
    let key = try privateKey()
    switch CommandLine.arguments[1] {
    case "public-key":
        print(key.publicKey.rawRepresentation.base64EncodedString())
    case "sign":
        guard CommandLine.arguments.count == 3,
              let catalog = FileManager.default.contents(
                atPath: CommandLine.arguments[2]
              ) else {
            throw SigningError.unreadableCatalog
        }
        print(try key.signature(for: catalog).base64EncodedString())
    default:
        throw SigningError.usage
    }
} catch {
    FileHandle.standardError.write(Data("\(error)\n".utf8))
    exit(1)
}
