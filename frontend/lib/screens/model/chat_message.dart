class ChatMessage {
  final String text;
  final bool isUser;
  final bool hasCaution;
  final DateTime timestamp;

  ChatMessage({
    required this.text,
    required this.isUser,
    this.hasCaution = false,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  Map<String, dynamic> toMap() {
    return {
      "text": text,
      "isUser": isUser,
      "hasCaution": hasCaution,
      // Stored as millis rather than a Firestore Timestamp because this map
      // lives inside an array field (arrayUnion doesn't play well with
      // FieldValue.serverTimestamp() inside array elements).
      "timestamp": timestamp.millisecondsSinceEpoch,
    };
  }

  factory ChatMessage.fromMap(Map<String, dynamic> map) {
    return ChatMessage(
      text: map["text"] ?? "",
      isUser: map["isUser"] ?? false,
      hasCaution: map["hasCaution"] ?? false,
      timestamp: map["timestamp"] != null
          ? DateTime.fromMillisecondsSinceEpoch(map["timestamp"])
          : DateTime.now(),
    );
  }
}