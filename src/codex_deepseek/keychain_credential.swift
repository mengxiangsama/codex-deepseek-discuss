import Foundation
import Security

let service = "codex.deepseek-discuss"
let account = NSUserName()
let mode = CommandLine.arguments.dropFirst().first ?? "get"

var query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrService as String: service,
    kSecAttrAccount as String: account,
]

if mode == "set" {
    let data = FileHandle.standardInput.readDataToEndOfFile()
    guard !data.isEmpty else {
        fputs("No credential received on stdin.\n", stderr)
        exit(2)
    }
    let update = [kSecValueData as String: data]
    let updateStatus = SecItemUpdate(query as CFDictionary, update as CFDictionary)
    if updateStatus == errSecItemNotFound {
        query[kSecValueData as String] = data
        query[kSecAttrLabel as String] = "DeepSeek key for Codex discussion MCP"
        let addStatus = SecItemAdd(query as CFDictionary, nil)
        guard addStatus == errSecSuccess else {
            fputs("Could not save credential to macOS Keychain (status \(addStatus)).\n", stderr)
            exit(3)
        }
    } else if updateStatus != errSecSuccess {
        fputs("Could not update credential in macOS Keychain (status \(updateStatus)).\n", stderr)
        exit(4)
    }
    print("DeepSeek key saved to macOS Keychain.")
} else if mode == "get" {
    query[kSecReturnData as String] = true
    query[kSecMatchLimit as String] = kSecMatchLimitOne
    var result: CFTypeRef?
    let status = SecItemCopyMatching(query as CFDictionary, &result)
    guard status == errSecSuccess, let data = result as? Data else {
        fputs("DeepSeek key was not found in macOS Keychain.\n", stderr)
        exit(status == errSecItemNotFound ? 5 : 6)
    }
    FileHandle.standardOutput.write(data)
} else {
    fputs("Usage: keychain_credential.swift [get|set]\n", stderr)
    exit(64)
}
