import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

import '../model/chat_message.dart';

class InMemoryConversation {
  final String id;
  String title;
  final String userType;
  final List<ChatMessage> messages;
  DateTime updatedAt;

  InMemoryConversation({
    required this.id,
    required this.title,
    required this.userType,
    required this.messages,
    required this.updatedAt,
  });
}

/// Holds chat history in memory for the lifetime of the app process.
///
/// This is a drop-in replacement for a Firestore-backed service: it exposes
/// the same shape of operations (create / append / list / delete), so if you
/// add Firestore (or any other backend) later, only this file needs to
/// change — persona pages and the sidebar widget don't.
///
/// LIMITATION: history is lost when the app is fully closed and restarted,
/// since nothing is written to disk.
class ConversationStore extends ChangeNotifier {
  ConversationStore._();
  static final ConversationStore instance = ConversationStore._();

  final Map<String, List<InMemoryConversation>> _byPersona = {};

  List<InMemoryConversation> conversationsFor(String userType) {
    final list = _byPersona[userType] ?? [];
    final sorted = List<InMemoryConversation>.from(list)
      ..sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return sorted;
  }

  InMemoryConversation createConversation({
    required String userType,
    required ChatMessage firstMessage,
  }) {
    final title = firstMessage.text.length > 60
        ? "${firstMessage.text.substring(0, 60)}..."
        : firstMessage.text;

    final convo = InMemoryConversation(
      id: const Uuid().v4(),
      title: title,
      userType: userType,
      messages: [firstMessage],
      updatedAt: DateTime.now(),
    );

    _byPersona.putIfAbsent(userType, () => []).add(convo);
    notifyListeners();
    return convo;
  }

  void appendMessage({
    required String userType,
    required String conversationId,
    required ChatMessage message,
  }) {
    final list = _byPersona[userType];
    if (list == null) return;
    final index = list.indexWhere((c) => c.id == conversationId);
    if (index == -1) return;

    list[index].messages.add(message);
    list[index].updatedAt = DateTime.now();
    notifyListeners();
  }

  List<ChatMessage> messagesFor({
    required String userType,
    required String conversationId,
  }) {
    final list = _byPersona[userType];
    if (list == null) return [];
    final index = list.indexWhere((c) => c.id == conversationId);
    if (index == -1) return [];
    return List.unmodifiable(list[index].messages);
  }

  void deleteConversation({
    required String userType,
    required String conversationId,
  }) {
    _byPersona[userType]?.removeWhere((c) => c.id == conversationId);
    notifyListeners();
  }
}