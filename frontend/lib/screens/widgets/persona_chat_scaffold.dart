import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../model/chat_message.dart';
import '../services/conversation_store.dart';
import '../../theme/app_colors.dart';
import 'conversation_sidebar.dart';



/// Conversation history is kept in-memory via [ConversationStore] 
class PersonaChatScaffold extends StatefulWidget {
  final String personaLabel; // shown in UI, e.g. "Practitioner"
  final String userTypeKey; // sent to backend, e.g. "practitioner"
  final Color accentColor;
  final IconData icon;
  final String greeting;
  final Widget? infoBanner;

  const PersonaChatScaffold({
    super.key,
    required this.personaLabel,
    required this.userTypeKey,
    required this.accentColor,
    required this.icon,
    required this.greeting,
    this.infoBanner,
  });

  @override
  State<PersonaChatScaffold> createState() => _PersonaChatScaffoldState();
}

class _PersonaChatScaffoldState extends State<PersonaChatScaffold> {
  final TextEditingController _controller = TextEditingController();
  final List<ChatMessage> _messages = [];
  bool _isLoading = false;

 
  final String backendUrl = "http://127.0.0.1:5000/api/ask";

  String? _conversationId; 

  Future<void> _sendMessage(String query) async {
    if (query.trim().isEmpty) return;

    final userMessage = ChatMessage(text: query, isUser: true);
    setState(() {
      _messages.add(userMessage);
      _isLoading = true;
    });
    _controller.clear();

    final isNewConversation = _conversationId == null;

    try {
      String sessionId = _conversationId ?? "";
      if (isNewConversation) {
        final convo = ConversationStore.instance.createConversation(
          userType: widget.userTypeKey,
          firstMessage: userMessage,
        );
        _conversationId = convo.id;
        sessionId = convo.id;
      } else {
        ConversationStore.instance.appendMessage(
          userType: widget.userTypeKey,
          conversationId: _conversationId!,
          message: userMessage,
        );
      }

      final response = await http.post(
        Uri.parse(backendUrl),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "query": query,
          "session_id": sessionId,
          "user_context": {"user_type": widget.userTypeKey},
        }),
      );

      late final ChatMessage botMessage;
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        botMessage = ChatMessage(
          text: data['answer'] ?? "Sorry, I couldn't get a response.",
          isUser: false,
          hasCaution: data['safety_context_available'] == true,
        );
      } else {
        botMessage = ChatMessage(
          text: "Server error: ${response.statusCode}",
          isUser: false,
        );
      }

      setState(() => _messages.add(botMessage));
      ConversationStore.instance.appendMessage(
        userType: widget.userTypeKey,
        conversationId: _conversationId!,
        message: botMessage,
      );
    } catch (e) {
      setState(() => _messages.add(
            ChatMessage(text: "Cannot connect to backend. Is it running?", isUser: false),
          ));
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _startNewConversation() {
    setState(() {
      _messages.clear();
      _conversationId = null;
    });
  }

  void _openConversation(String conversationId) {
    final messages = ConversationStore.instance.messagesFor(
      userType: widget.userTypeKey,
      conversationId: conversationId,
    );
    setState(() {
      _messages
        ..clear()
        ..addAll(messages);
      _conversationId = conversationId;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
  // ========== BACK ARROW ==========
    leading: IconButton(
    icon: const Icon(Icons.arrow_back, color: Colors.white),
    onPressed: () {
      // Goes all the way back to Home
      Navigator.of(context).popUntil((route) => route.isFirst);
    },
    tooltip: 'Back',
  ),
  title: Row(
    children: [
      Icon(widget.icon, size: 20),
      const SizedBox(width: 8),
      Text(widget.personaLabel),
    ],
  ),
  backgroundColor: widget.accentColor,
  foregroundColor: Colors.white,
  centerTitle: false,
  actions: [
    IconButton(
      icon: const Icon(Icons.add_comment_outlined),
      onPressed: _startNewConversation,
      tooltip: "New Conversation",
    ),
  ],
),
      drawer: ConversationSidebar(
        userType: widget.userTypeKey,
        personaLabel: widget.personaLabel,
        activeConversationId: _conversationId,
        accentColor: widget.accentColor,
        onSelect: _openConversation,
        onNewConversation: _startNewConversation,
      ),
      body: SafeArea(
        child: Column(
          children: [
            if (widget.infoBanner != null) widget.infoBanner!,
            Expanded(
              child: _messages.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(widget.icon, size: 58, color: widget.accentColor),
                            const SizedBox(height: 16),
                            Text(
                              widget.greeting,
                              style: const TextStyle(
                                color: AppColors.muted,
                                fontWeight: FontWeight.w700,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: _messages.length,
                      itemBuilder: (context, index) {
                        final msg = _messages[index];
                        return Align(
                          alignment: msg.isUser
                              ? Alignment.centerRight
                              : Alignment.centerLeft,
                          child: Container(
                            margin: const EdgeInsets.symmetric(vertical: 6),
                            padding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 12),
                            constraints: BoxConstraints(
                              maxWidth: MediaQuery.of(context).size.width * 0.78,
                            ),
                            decoration: BoxDecoration(
                              color: msg.isUser
                                  ? widget.accentColor
                                  : const Color(0xFFF1F1F1),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (!msg.isUser && msg.hasCaution)
                                  Padding(
                                    padding: const EdgeInsets.only(bottom: 6),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        const Icon(Icons.warning_amber_rounded,
                                            size: 16, color: Color(0xFFE99A1E)),
                                        const SizedBox(width: 4),
                                        Text(
                                          "Includes a safety caution",
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.bold,
                                            color: Colors.orange[800],
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                Text(
                                  msg.text,
                                  style: TextStyle(
                                    color: msg.isUser ? Colors.white : AppColors.text,
                                    fontSize: 16,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
            ),
            if (_isLoading)
              const Padding(
                padding: EdgeInsets.all(8.0),
                child: CircularProgressIndicator(),
              ),
            Padding(
              padding: const EdgeInsets.all(12.0),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: InputDecoration(
                        hintText: "Ask about plants or diseases...",
                        border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(25)),
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 20, vertical: 12),
                      ),
                      onSubmitted: _sendMessage,
                    ),
                  ),
                  const SizedBox(width: 8),
                  FloatingActionButton(
                    onPressed: () => _sendMessage(_controller.text),
                    backgroundColor: widget.accentColor,
                    child: const Icon(Icons.send, color: Colors.white),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}