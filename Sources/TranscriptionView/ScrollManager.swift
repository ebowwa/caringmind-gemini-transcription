import SwiftUI

/// ScrollManager: Manages scrolling to specific views in the app
/// Uses a namespace ID approach for precise view targeting
@MainActor
final class ScrollManager: ObservableObject, @unchecked Sendable {
    static let shared = ScrollManager()
    
    @Published private var activeScrollTarget: String?
    private var scrollProxy: ScrollViewProxy?
    
    private init() {}
    
    /// Sets the scroll view proxy for managing scroll positions
    /// - Parameter proxy: The ScrollViewProxy to use for scrolling
    func setScrollProxy(_ proxy: ScrollViewProxy) {
        self.scrollProxy = proxy
    }
    
    /// Scrolls to a specific view identified by its namespace ID
    /// - Parameters:
    ///   - id: The namespace ID of the target view
    ///   - anchor: The anchor point for scrolling (default: .center)
    ///   - animated: Whether to animate the scroll (default: true)
    func scrollTo<ID: Hashable>(
        _ id: ID,
        anchor: UnitPoint = .center,
        animated: Bool = true
    ) {
        guard let proxy = scrollProxy else { return }
        
        if animated {
            withAnimation {
                proxy.scrollTo(id, anchor: anchor)
            }
        } else {
            proxy.scrollTo(id, anchor: anchor)
        }
    }
    
    /// Scrolls to the typing indicator view
    /// - Parameter animated: Whether to animate the scroll
    func scrollToTypingIndicator(animated: Bool = true) {
        scrollTo("typingIndicator", anchor: .bottom, animated: animated)
    }
}
