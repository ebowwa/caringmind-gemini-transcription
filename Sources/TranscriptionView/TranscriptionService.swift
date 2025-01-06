import Foundation

// Base protocol for audio LLM responses
protocol AudioLLMModelResponseStructure: Codable {
    associatedtype AnalysisType: Codable
    var fullAudioTranscribed: Bool { get }
    var conversationAnalysis: [AnalysisType] { get }
}

// Response models matching the Python backend
struct TranscriptionResponse: AudioLLMModelResponseStructure {
    let fullAudioTranscribed: Bool
    let conversationAnalysis: [ConversationTurn]
    
    enum CodingKeys: String, CodingKey {
        case fullAudioTranscribed = "full_audio_transcribed"
        case conversationAnalysis = "conversation_analysis"
    }
}

struct ConversationTurn: Codable, Identifiable {
    let id = UUID()  // Add unique identifier
    let diarizationHtml: String
    let transcriptionHtml: String
    let timestampsHtml: String
    let toneAnalysis: ToneAnalysis
    let confidence: Double
    let summary: String
    
    enum CodingKeys: String, CodingKey {
        case id
        case diarizationHtml = "diarization_html"
        case transcriptionHtml = "transcription_html"
        case timestampsHtml = "timestamps_html"
        case toneAnalysis = "tone_analysis"
        case confidence
        case summary
    }
}

struct ToneAnalysis: Codable {
    let tone: String
    let indicators: [String]
}

enum TranscriptionError: Error {
    case serverError(String)
    case conversionError
}

@globalActor actor TranscriptionActor {
    static let shared = TranscriptionActor()
}

@TranscriptionActor
final class TranscriptionService: @unchecked Sendable {
    static let shared = TranscriptionService()
    private let baseURL: URL
    
    private init() {
        self.baseURL = URL(string: "https://1682-73-15-186-2.ngrok-free.app")!
    }
    
    func transcribeAudio(fileURL: URL) async throws -> TranscriptionResponse {
        // Read audio file
        let audioData = try Data(contentsOf: fileURL)
        let base64Audio = audioData.base64EncodedString()
        
        // Prepare request
        var request = URLRequest(url: baseURL.appendingPathComponent("/upload"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Create request body
        struct RequestBody: Encodable {
            let audio_base64: String
        }
        let requestBody = RequestBody(audio_base64: base64Audio)
        request.httpBody = try JSONEncoder().encode(requestBody)
        
        // Make request
        let (data, response) = try await URLSession.shared.data(for: request)
        
        // Handle response
        guard let httpResponse = response as? HTTPURLResponse else {
            throw TranscriptionError.serverError("Invalid response type")
        }
        
        // Check for error responses
        if !(200...299).contains(httpResponse.statusCode) {
            if let errorJson = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let detail = errorJson["detail"] as? String {
                throw TranscriptionError.serverError(detail)
            }
            throw TranscriptionError.serverError("Server error \(httpResponse.statusCode)")
        }
        
        // Decode response
        let decoder = JSONDecoder()
        return try decoder.decode(TranscriptionResponse.self, from: data)
    }
}
