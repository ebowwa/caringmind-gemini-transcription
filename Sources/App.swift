import SwiftUI

@main
struct GeminiTranscriptionApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
// roughly this is my understanding of this app so far, which is important as i have a larger app which i intend to integrate this into 
// Currently, the structure is:
// - App.swift : main entry point; calls the contentview; handles windowgroup
// - ContentView.swift : main UI for the app; AudioRecorder, RecordButton and ConversationCard; should only handle the navigationview and nothing else
// - SceneDelegate.swift : ??? teach me what this does
// - TranscriptionService.swift : handles the api calls with the backend 