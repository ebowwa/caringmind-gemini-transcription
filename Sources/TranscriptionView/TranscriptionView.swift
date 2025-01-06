import SwiftUI

struct TranscriptionView: View {
    @StateObject private var audioRecorder = AudioRecorder()
    @StateObject private var scrollManager = ScrollManager.shared
    
    var body: some View {
        TranscriptionViewContent(audioRecorder: audioRecorder)
    }
}

private struct TranscriptionViewContent: View {
    let audioRecorder: AudioRecorder
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                TranscriptionScrollView(audioRecorder: audioRecorder)
                TranscriptionControlsView(audioRecorder: audioRecorder)
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text(audioRecorder.isProcessing ? "Transcribing..." : "Voice Notes")
                        .font(.headline)
                }
            }
        }
    }
}

private struct TranscriptionScrollView: View {
    let audioRecorder: AudioRecorder
    
    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 8) {
                    if let result = audioRecorder.transcriptionResult {
                        ForEach(result.conversationAnalysis) { turn in
                            MessageBubble(text: turn.transcriptionHtml)
                                .id(turn.id)
                        }
                    }
                    
                    if audioRecorder.isProcessing {
                        TypingIndicatorView()
                            .id("typingIndicator")
                            .padding(.horizontal)
                    }
                }
                .padding(.horizontal)
            }
            .onChange(of: audioRecorder.isProcessing) { isProcessing in
                if isProcessing {
                    withAnimation {
                        proxy.scrollTo("typingIndicator", anchor: .bottom)
                    }
                }
            }
        }
    }
}

private struct TranscriptionControlsView: View {
    let audioRecorder: AudioRecorder
    
    var body: some View {
        VStack(spacing: 8) {
            if let error = audioRecorder.error {
                Text(error.localizedDescription)
                    .font(.caption)
                    .foregroundColor(.red)
                    .padding(.horizontal)
            }
            
            HStack(spacing: 16) {
                RecordButton(audioRecorder: audioRecorder)
                    .frame(width: 44, height: 44)
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
            .background(Color(.systemBackground))
            .overlay(
                Divider()
                    .padding(.horizontal, -16),
                alignment: .top
            )
        }
    }
}

struct MessageBubble: View {
    let text: String
    
    var body: some View {
        HStack {
            Text(text)
                .padding(12)
                .background(Color.blue)
                .foregroundColor(.white)
                .clipShape(BubbleShape())
                .padding(.leading, 60)
        }
        .frame(maxWidth: .infinity, alignment: .trailing)
        .padding(.vertical, 4)
    }
}

struct BubbleShape: Shape {
    func path(in rect: CGRect) -> Path {
        let path = UIBezierPath(
            roundedRect: rect,
            byRoundingCorners: [.topLeft, .topRight, .bottomLeft],
            cornerRadii: CGSize(width: 16, height: 16)
        )
        return Path(path.cgPath)
    }
}

struct TypingIndicatorView: View {
    @State private var animationOffset: CGFloat = 0
    
    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3) { index in
                Circle()
                    .fill(Color.gray.opacity(0.5))
                    .frame(width: 8, height: 8)
                    .offset(y: animationOffset)
                    .animation(
                        Animation.easeInOut(duration: 0.6)
                            .repeatForever()
                            .delay(0.2 * Double(index)),
                        value: animationOffset
                    )
            }
        }
        .padding(8)
        .background(Color(.systemGray6))
        .clipShape(Capsule())
        .onAppear {
            animationOffset = -5
        }
    }
}
