import AVFoundation
import Foundation

/// Apple STT Microservice
/// Runs on macOS and exposes Apple Speech Framework via REST API
/// Communicates with main FastAPI service

let app = try await Application.make()

// Health check endpoint
app.get("health") { req -> JSONResponse in
    return JSONResponse(status: "ok", service: "Apple STT Service")
}

// Transcription endpoint
app.post("v1", "transcribe") { req -> JSONResponse in
    guard let audioData = try req.content.get(Data.self, at: "audio") else {
        throw Abort(.badRequest, reason: "Audio data required")
    }

    let language = try req.content.get(String.self, at: "language") ?? "en-US"

    // Use Apple Speech Framework
    let recognizer = SFSpeechRecognizer(locale: Locale(identifier: language))
    guard let recognizer = recognizer, recognizer.isAvailable else {
        throw Abort(.serviceUnavailable, reason: "Speech recognition not available")
    }

    // Save audio to temporary file
    let tempFile = URL(fileURLWithPath: "/tmp/audio_\(UUID().uuidString).wav")
    try audioData.write(to: tempFile)

    // Create recognition request
    let request = SFSpeechURLRecognitionRequest(url: tempFile)
    request.shouldReportPartialResults = false

    var transcript = ""
    var confidence: Float = 0.0

    let semaphore = DispatchSemaphore(value: 0)

    recognizer.recognitionTask(with: request) { result, error in
        if let error = error {
            print("❌ Transcription error: \(error)")
            semaphore.signal()
            return
        }

        if let result = result {
            transcript = result.bestTranscription.formattedString
            confidence = result.isFinal ? 0.95 : 0.5
        }

        if result?.isFinal ?? false {
            semaphore.signal()
        }
    }.resume()

    // Wait for transcription
    _ = semaphore.wait(timeout: .now() + 120)

    // Clean up
    try? FileManager.default.removeItem(at: tempFile)

    return JSONResponse(
        transcript: transcript,
        confidence: confidence,
        language: language,
        provider: "apple_stt"
    )
}

// Info endpoint
app.get("v1", "info") { req -> JSONResponse in
    return JSONResponse(
        service: "Apple STT Microservice",
        version: "1.0.0",
        provider: "apple_stt",
        capabilities: ["transcription", "multilingual"]
    )
}

try await app.run()

// MARK: - Helper Types

struct JSONResponse: Codable {
    let status: String?
    let service: String?
    let transcript: String?
    let confidence: Float?
    let language: String?
    let provider: String?
    let version: String?
    let capabilities: [String]?

    init(
        status: String? = nil,
        service: String? = nil,
        transcript: String? = nil,
        confidence: Float? = nil,
        language: String? = nil,
        provider: String? = nil,
        version: String? = nil,
        capabilities: [String]? = nil
    ) {
        self.status = status
        self.service = service
        self.transcript = transcript
        self.confidence = confidence
        self.language = language
        self.provider = provider
        self.version = version
        self.capabilities = capabilities
    }

    enum CodingKeys: String, CodingKey {
        case status, service, transcript, confidence, language, provider, version, capabilities
    }
}
