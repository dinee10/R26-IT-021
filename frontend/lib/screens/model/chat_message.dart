class ChatMessage {
  final String text;
  final bool isUser;
  final bool hasCaution;
  final DateTime timestamp;

  final List<String> personas;

  ChatMessage({
    required this.text,
    required this.isUser,
    this.hasCaution = false,
    this.personas = const [],
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  Map<String, dynamic> toMap() {
    return {
      "text": text,
      "isUser": isUser,
      "hasCaution": hasCaution,
      "personas": personas,
      "timestamp": timestamp.millisecondsSinceEpoch,
    };
  }

  factory ChatMessage.fromMap(Map<String, dynamic> map) {
    return ChatMessage(
      text: map["text"] ?? "",
      isUser: map["isUser"] ?? false,
      hasCaution: map["hasCaution"] ?? false,
      personas: List<String>.from(map["personas"] ?? const []),
      timestamp: map["timestamp"] != null
          ? DateTime.fromMillisecondsSinceEpoch(map["timestamp"])
          : DateTime.now(),
    );
  }
}