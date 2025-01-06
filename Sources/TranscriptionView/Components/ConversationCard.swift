import SwiftUI
// Should only show the timestamp, transcription, and diarization unless the card is tapped for more information. Then show the rest
struct ConversationCard: View {
    let turn: ConversationTurn
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Speaker and Time
            HStack {
                Text(cleanHTML(turn.diarizationHtml))
                    .font(.title3.bold())
                Spacer()
                Text(cleanHTML(turn.timestampsHtml))
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            // Transcription
            Text(cleanHTML(turn.transcriptionHtml))
                .font(.body)
                .padding(.vertical, 2)
            
            // Tone Analysis
            HStack(spacing: 8) {
                Text("Tone: ")
                    .foregroundColor(.secondary)
                Text(turn.toneAnalysis.tone)
                    .foregroundColor(.blue)
            }
            .font(.subheadline)
            
            // Indicators
            ForEach(turn.toneAnalysis.indicators, id: \.self) { indicator in
                Text("• " + indicator)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Divider()
            
            // Summary
            Text(turn.summary)
                .font(.callout)
                .foregroundColor(.secondary)
            
            // Confidence
            HStack {
                Spacer()
                Text("\(Int(turn.confidence))% confidence")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color(.systemBackground))
                .shadow(color: .black.opacity(0.1), radius: 10, x: 0, y: 2)
        )
    }
    
    private func cleanHTML(_ html: String) -> String {
        html.replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
    }
}
