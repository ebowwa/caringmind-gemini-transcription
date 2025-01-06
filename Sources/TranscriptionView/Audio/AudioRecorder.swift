import Foundation
import AVFoundation

@MainActor
class AudioRecorder: ObservableObject {
    private var audioRecorder: AVAudioRecorder?
    @Published var isRecording = false
    @Published var transcriptionResult: TranscriptionResponse?
    @Published var isProcessing = false
    @Published var error: Error?
    
    private let audioSession = AVAudioSession.sharedInstance()
    
    init() {
        setupAudioSession()
    }
    
    private func setupAudioSession() {
        do {
            try audioSession.setCategory(.playAndRecord, mode: .default)
            try audioSession.setActive(true)
        } catch {
            print("Failed to set up audio session: \(error)")
        }
    }
    
    func startRecording() {
        let audioFilename = getDocumentsDirectory().appendingPathComponent("recording.m4a")
        let settings = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        
        do {
            audioRecorder = try AVAudioRecorder(url: audioFilename, settings: settings)
            audioRecorder?.record()
            isRecording = true
            transcriptionResult = nil
            error = nil
        } catch {
            print("Could not start recording: \(error)")
            self.error = error
        }
    }
    
    func stopRecording() {
        let recordingURL = audioRecorder?.url
        audioRecorder?.stop()
        isRecording = false
        
        guard let url = recordingURL else { return }
        
        Task {
            isProcessing = true
            do {
                let result = try await TranscriptionService.shared.transcribeAudio(fileURL: url)
                await MainActor.run {
                    self.transcriptionResult = result
                    self.isProcessing = false
                }
            } catch {
                await MainActor.run {
                    self.error = error
                    self.isProcessing = false
                }
            }
        }
    }
    
    private func getDocumentsDirectory() -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }
}
