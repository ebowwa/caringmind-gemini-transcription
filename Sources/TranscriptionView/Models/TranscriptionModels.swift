import Foundation

struct TranscriptionSegment: Identifiable {
    let id: UUID
    let text: String
    let timestamp: Date
    let isFinal: Bool
    let conversationId: UUID
}

struct AudioMetadata {
    var duration: TimeInterval = 0
    var format: String = "m4a"
    var sampleRate: Double = 44100
    var channels: Int = 1
}
    /**
struct TranscriptionResponse: Codable {
    let text: String
    let confidence: Float
}
*/
