class ConversationSummary {
  final String id;
  final String title;
  final String userType;
  final DateTime updatedAt;

  ConversationSummary({
    required this.id,
    required this.title,
    required this.userType,
    required this.updatedAt,
  });

  factory ConversationSummary.fromFirestore(
      String id, Map<String, dynamic> data) {
    return ConversationSummary(
      id: id,
      title: (data["title"] as String?)?.trim().isNotEmpty == true
          ? data["title"]
          : "New conversation",
      userType: data["userType"] ?? "",
      updatedAt: data["updatedAt"] != null
          ? (data["updatedAt"] as dynamic).toDate()
          : DateTime.now(),
    );
  }
}