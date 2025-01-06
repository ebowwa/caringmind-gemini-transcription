import SwiftUI

struct RecordButton: View {
    @ObservedObject var audioRecorder: AudioRecorder
    
    var body: some View {
        Button(action: {
            if audioRecorder.isRecording {
                audioRecorder.stopRecording()
            } else {
                audioRecorder.startRecording()
            }
        }) {
            ZStack {
                Circle()
                    .fill(audioRecorder.isRecording ? Color.red.opacity(0.1) : Color.blue.opacity(0.1))
                    .frame(width: 120, height: 120)
                
                Circle()
                    .stroke(audioRecorder.isRecording ? Color.red : Color.blue, lineWidth: 3)
                    .frame(width: 120, height: 120)
                
                Image(systemName: audioRecorder.isRecording ? "stop.fill" : "mic.fill")
                    .font(.system(size: 40))
                    .foregroundColor(audioRecorder.isRecording ? .red : .blue)
            }
        }
        .disabled(audioRecorder.isProcessing)
    }
}
