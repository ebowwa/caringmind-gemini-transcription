import SwiftUI
import AVFoundation

struct TranscriptionView: View {
    @StateObject private var viewModel = TranscriptionViewModel()
    @StateObject private var audioRecorder: AudioRecorder
    @State private var isMetadataVisible: Bool = false
    @State private var lastSegmentId: UUID? = nil
    
    init() {
        _audioRecorder = StateObject(wrappedValue: AudioRecorder())
    }
    
    var body: some View {
        VStack {
            // Header
            HStack {
                Button(action: { isMetadataVisible.toggle() }) {
                    Image(systemName: "info.circle")
                        .font(.title2)
                }
                
                Spacer()
                
                Text("Audio Analysis")
                    .font(.headline)
                
                Spacer()
                
                Button(action: {
                    if viewModel.isTranscribing {
                        viewModel.stopRecording()
                    } else {
                        viewModel.startRecording()
                    }
                }) {
                    Image(systemName: viewModel.isTranscribing ? "stop.circle.fill" : "mic.circle.fill")
                        .font(.title)
                        .foregroundColor(viewModel.isTranscribing ? .red : .blue)
                }
            }
            .padding()
            
            // Transcription List
            ScrollView {
                ScrollViewReader { proxy in
                    LazyVStack(alignment: .leading, spacing: 12) {
                        ForEach(viewModel.transcriptionSegments) { segment in
                            TranscriptionSegmentView(
                                segment: segment,
                                formatter: viewModel.naturalLanguageTimeSince
                            )
                            .id(segment.id)
                        }
                        
                        if viewModel.isTranscribing {
                            TypingIndicatorView()
                                .id("typingIndicator")
                        }
                    }
                    .padding()
                    .onChange(of: viewModel.transcriptionSegments) { _ in
                        withAnimation {
                            proxy.scrollTo("typingIndicator", anchor: .bottom)
                        }
                    }
                }
            }
            
            if isMetadataVisible {
                AudioMetadataView(metadata: viewModel.audioMetadata)
                    .transition(.move(edge: .bottom))
            }
            
            Spacer()
            
            if audioRecorder.isProcessing {
                ProgressView("Analyzing...")
                    .padding(.top, 20)
            }
            
            if let error = audioRecorder.error {
                Text(error.localizedDescription)
                    .foregroundColor(.red)
                    .padding()
            }
            
            if let result = audioRecorder.transcriptionResult {
                ScrollView {
                    ScrollViewReader { proxy in
                        LazyVStack(spacing: 16) {
                            ForEach(result.conversationAnalysis, id: \.transcriptionHtml) { turn in
                                ConversationCard(turn: turn)
                            }
                        }
                        .padding(.horizontal)
                    }
                }
            }
        }
        .alert("Server Error", isPresented: $viewModel.showServerError) {
            Button("OK", role: .cancel) { }
        } message: {
            Text(viewModel.serverErrorMessage)
        }
    }
}

struct TranscriptionSegmentView: View {
    let segment: TranscriptionSegment
    let formatter: (Date) -> String
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(formatter(segment.timestamp))
                .font(.caption)
                .foregroundColor(.secondary)
            
            HStack {
                Text(segment.text)
                    .padding(10)
                    .background(segment.isFinal ? Color.blue : Color.blue.opacity(0.3))
                    .foregroundColor(.white)
                    .cornerRadius(15)
                
                Spacer()
            }
        }
        .transition(.asymmetric(
            insertion: .scale(scale: 0.9).combined(with: .opacity),
            removal: .opacity
        ))
    }
}

struct TypingIndicatorView: View {
    @State private var dotCount = 0
    
    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3) { index in
                Circle()
                    .fill(Color.gray)
                    .frame(width: 8, height: 8)
                    .opacity(dotCount >= index ? 1 : 0.3)
            }
        }
        .padding(8)
        .background(Color.gray.opacity(0.2))
        .cornerRadius(12)
        .onAppear {
            withAnimation(Animation.easeInOut(duration: 0.6).repeatForever()) {
                dotCount = 3
            }
        }
    }
}

struct AudioMetadataView: View {
    let metadata: AudioMetadata
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Audio Metadata")
                .font(.headline)
            
            Group {
                InfoRow(label: "Duration", value: String(format: "%.1f sec", metadata.duration))
                InfoRow(label: "Format", value: metadata.format)
                InfoRow(label: "Sample Rate", value: "\(Int(metadata.sampleRate)) Hz")
                InfoRow(label: "Channels", value: "\(metadata.channels)")
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(radius: 2)
    }
}

struct InfoRow: View {
    let label: String
    let value: String
    
    var body: some View {
        HStack {
            Text(label)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
        }
    }
}
