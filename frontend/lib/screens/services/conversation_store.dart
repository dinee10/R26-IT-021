import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
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

/// Keeps the existing synchronous UI API while synchronizing each signed-in
/// user's conversations with Cloud Firestore.
///
/// Firestore path: users/{firebaseAuthUid}/conversations/{conversationId}
/// Each conversation is ONE document containing a `messages` array. Deleting
/// that document therefore deletes its stored messages too.
///
/// This layout is appropriate for short/medium research-demo conversations;
/// Firestore documents have a 1 MiB size limit. A production-scale chat app
/// should use a message subcollection with explicit recursive deletion.
class ConversationStore extends ChangeNotifier {
  ConversationStore._() {
    _authSubscription = FirebaseAuth.instance.authStateChanges().listen(
      _handleAuthChange,
      onError: (Object error) => _reportError('Authentication listener', error),
    );
  }

  static final ConversationStore instance = ConversationStore._();

  final Map<String, List<InMemoryConversation>> _byPersona = {};
  final Map<String, Future<void>> _pendingWrites = {};
  StreamSubscription<User?>? _authSubscription;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>?
      _conversationsSubscription;
  int _listenerGeneration = 0;
  String? _lastSyncError;

  /// Can be displayed in the UI if a Firestore read/write fails.
  String? get lastSyncError => _lastSyncError;

  CollectionReference<Map<String, dynamic>> _collection(String uid) =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('conversations');

  void _reportError(String action, Object error) {
    _lastSyncError = '$action failed: $error';
    debugPrint('[ConversationStore] $_lastSyncError');
    notifyListeners();
  }

  void _handleAuthChange(User? user) {
    final generation = ++_listenerGeneration;
    final previousListener = _conversationsSubscription;
    if (previousListener != null) unawaited(previousListener.cancel());
    _conversationsSubscription = null;
    _byPersona.clear();
    _lastSyncError = null;
    notifyListeners();

    if (user == null) return;

    _conversationsSubscription = _collection(user.uid).snapshots().listen(
      (snapshot) {
        if (generation != _listenerGeneration) return;
        final loaded = <String, List<InMemoryConversation>>{};

        for (final document in snapshot.docs) {
          final data = document.data();
          final rawMessages = data['messages'];
          final messages = <ChatMessage>[];

          if (rawMessages is List) {
            for (final rawMessage in rawMessages) {
              if (rawMessage is Map) {
                try {
                  messages.add(ChatMessage.fromMap(
                    Map<String, dynamic>.from(rawMessage),
                  ));
                } catch (error) {
                  debugPrint('[ConversationStore] Skipped invalid message: $error');
                }
              }
            }
          }

          final userType = data['userType'] is String
              ? data['userType'] as String
              : 'general_public';
          final updated = data['updatedAt'];
          final updatedAt = updated is Timestamp
              ? updated.toDate()
              : DateTime.now();

          loaded.putIfAbsent(userType, () => []).add(InMemoryConversation(
                id: document.id,
                title: data['title'] is String
                    ? data['title'] as String
                    : 'New conversation',
                userType: userType,
                messages: messages,
                updatedAt: updatedAt,
              ));
        }

        _byPersona
          ..clear()
          ..addAll(loaded);
        _lastSyncError = null;
        notifyListeners();
      },
      onError: (Object error) {
        if (generation == _listenerGeneration) {
          _reportError('Loading conversations', error);
        }
      },
    );
  }

  void _queueWrite(String conversationId, Future<void> Function() operation) {
    // Preserve ordering: creating a conversation must finish before appending
    // a reply, and a pending append must finish before deletion.
    final previous = _pendingWrites[conversationId] ?? Future<void>.value();
    final next = previous.then((_) => operation()).catchError(
      (Object error) => _reportError('Saving conversation', error),
    );
    _pendingWrites[conversationId] = next;
    unawaited(next.then((_) {
      if (identical(_pendingWrites[conversationId], next)) {
        _pendingWrites.remove(conversationId);
      }
    }));
  }

  List<InMemoryConversation> conversationsFor(String userType) {
    final sorted = List<InMemoryConversation>.from(_byPersona[userType] ?? []);
    sorted.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return sorted;
  }

  InMemoryConversation createConversation({
    required String userType,
    required ChatMessage firstMessage,
  }) {
    final now = DateTime.now();
    final title = firstMessage.text.length > 60
        ? '${firstMessage.text.substring(0, 60)}...'
        : firstMessage.text;
    final convo = InMemoryConversation(
      id: const Uuid().v4(),
      title: title,
      userType: userType,
      messages: [firstMessage],
      updatedAt: now,
    );

    _byPersona.putIfAbsent(userType, () => []).add(convo);
    notifyListeners();

    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) {
      _reportError('Saving conversation', 'No signed-in Firebase user');
    } else {
      _queueWrite(convo.id, () => _collection(uid).doc(convo.id).set({
            'title': title,
            'userType': userType,
            'createdAt': Timestamp.fromDate(now),
            'updatedAt': Timestamp.fromDate(now),
            'messages': [firstMessage.toMap()],
          }));
    }
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

    final now = DateTime.now();
    list[index].messages.add(message);
    list[index].updatedAt = now;
    notifyListeners();

    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) {
      _reportError('Saving message', 'No signed-in Firebase user');
    } else {
      _queueWrite(conversationId, () =>
          _collection(uid).doc(conversationId).set({
            'updatedAt': Timestamp.fromDate(now),
            'messages': FieldValue.arrayUnion([message.toMap()]),
          }, SetOptions(merge: true)));
    }
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

    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) {
      _reportError('Deleting conversation', 'No signed-in Firebase user');
    } else {
      // Messages are stored INSIDE this document: one delete removes all.
      _queueWrite(conversationId,
          () => _collection(uid).doc(conversationId).delete());
    }
  }

  @override
  void dispose() {
    final auth = _authSubscription;
    final firestore = _conversationsSubscription;
    if (auth != null) unawaited(auth.cancel());
    if (firestore != null) unawaited(firestore.cancel());
    super.dispose();
  }
}
