import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../model/chat_message.dart';
import '../services/conversation_store.dart';
import '../../theme/app_colors.dart';
import '../../services/plant_api.dart';
import 'conversation_sidebar.dart';
import 'persona_meta.dart';

/// Chat screen for one user type (page). Constructor is unchanged, so the four
/// existing pages (General Public / Practitioner / Student / Researcher) keep working.
///
/// Inside a page:
///  - Auto (default): answers as this page's user type. If a message asks for
///    another style (e.g. a Student asks for the scientific evidence), the
///    backend answers as that type for that answer only.
///  - Chips: the user can pick up to [kMaxCategories] styles explicitly; the
///    choice stays until they tap Auto.
/// Conversation history is kept in-memory via [ConversationStore].
class PersonaChatScaffold extends StatefulWidget {
  final String personaLabel; // shown in UI, e.g. "Practitioner"
  final String userTypeKey; // this page's home category, e.g. "practitioner"
  final Color accentColor;
  final IconData icon;
  final String greeting;
  final String? initialMessage;
  final Widget? infoBanner;

  const PersonaChatScaffold({
    super.key,
    required this.personaLabel,
    required this.userTypeKey,
    required this.accentColor,
    required this.icon,
    required this.greeting,
    this.initialMessage,
    this.infoBanner,
  });

  @override
  State<PersonaChatScaffold> createState() => _PersonaChatScaffoldState();
}

class _PersonaChatScaffoldState extends State<PersonaChatScaffold> {
  final TextEditingController _controller = TextEditingController();
  final List<ChatMessage> _messages = [];
  bool _isLoading = false;
  bool _initialMessageSent = false;

  String? _conversationId;

  /// User's explicit style choice from the chips. Empty = Auto.
  final List<String> _selected = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final message = widget.initialMessage?.trim();
      if (!mounted ||
          _initialMessageSent ||
          message == null ||
          message.isEmpty) {
        return;
      }

      _initialMessageSent = true;
      _sendMessage(message);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _sendMessage(String query) async {
  if (query.trim().isEmpty) return;

  // Capture recent messages before adding the current question.
  // These may have been restored from Firestore.
  final recentHistory = _messages
      .skip(_messages.length > 6 ? _messages.length - 6 : 0)
      .map((message) => {
            "role": message.isUser ? "user" : "assistant",
            "content": message.text,
          })
      .toList();

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

      final response = await http
          .post(
            Uri.parse('${PlantApi.baseUrl}/api/ask'),
            headers: {"Content-Type": "application/json"},
            body: jsonEncode({
              "query": query,
              "session_id": sessionId,
              "history": recentHistory,
              "user_context": {
                // "auto" => backend may switch style per message;
                // a list => explicit choice from the chips
                "user_type": _selected.isEmpty ? "auto" : _selected,
                // this page's own user type = the default style
                "default_type": widget.userTypeKey,
              },
            }),
          )
          .timeout(const Duration(seconds: 60));

      ChatMessage botMessage;
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final used = ((data['user_types'] as List?) ?? const [])
            .map((e) => e.toString())
            .where(isKnownPersona)
            .toList();
        botMessage = ChatMessage(
          text: data['answer'] ?? "Sorry, I couldn't get a response.",
          isUser: false,
          hasCaution: data['answer_has_caution'] == true,
          personas: used,
        );
      } else {
        botMessage = ChatMessage(text: _serverError(response), isUser: false);
      }

      if (!mounted) return;
      setState(() => _messages.add(botMessage));
      ConversationStore.instance.appendMessage(
        userType: widget.userTypeKey,
        conversationId: _conversationId!,
        message: botMessage,
      );
    } catch (e) {
      if (!mounted) return;
      setState(
        () => _messages.add(
          ChatMessage(
            text: 'Cannot connect to ${PlantApi.baseUrl}. '
                'Check that the backend is running.',
            isUser: false,
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  String _serverError(http.Response response) {
    try {
      final body = jsonDecode(response.body);
      if (body is Map<String, dynamic> && body['error'] is String) {
        return body['error'] as String;
      }
    } catch (_) {}
    return 'Server error: ${response.statusCode}';
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

  // ---------- new UI pieces ----------

  Widget _styleChips() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            ChoiceChip(
              avatar: const Icon(Icons.auto_awesome, size: 16),
              label: const Text("Auto"),
              selected: _selected.isEmpty,
              selectedColor: widget.accentColor.withValues(alpha: 0.18),
              onSelected: (_) => setState(() => _selected.clear()),
            ),
            for (final p in kPersonas) ...[
              const SizedBox(width: 8),
              FilterChip(
                avatar: Icon(p.icon, size: 16, color: p.color),
                label: Text(p.label),
                selected: _selected.contains(p.key),
                selectedColor: p.color.withValues(alpha: 0.18),
                checkmarkColor: p.color,
                onSelected: (_) =>
                    setState(() => togglePersona(_selected, p.key)),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _styleStatus() {
    final auto = _selected.isEmpty;
    final names = _selected.map((k) => personaByKey(k).label).join(" + ");
    return Container(
      width: double.infinity,
      color: widget.accentColor.withValues(alpha: 0.06),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(
        children: [
          Icon(auto ? Icons.auto_awesome : Icons.tune,
              size: 14, color: widget.accentColor),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              auto
                  ? "Auto: answering as ${widget.personaLabel}. Ask for another "
                      "style (e.g. \"explain the evidence\") and I'll switch for "
                      "that answer."
                  : "Your choice: $names. Tap Auto to go back to "
                      "${widget.personaLabel}.",
              style: const TextStyle(fontSize: 11, color: AppColors.text),
            ),
          ),
        ],
      ),
    );
  }

  /// Shown only when the answer used a style other than this page's own.
  String? _answeredAsLabel(ChatMessage msg) {
    if (msg.isUser || msg.personas.isEmpty) return null;
    if (msg.personas.length == 1 && msg.personas.first == widget.userTypeKey) {
      return null;
    }
    return "Answered as ${msg.personas.map((k) => personaByKey(k).label).join(' + ')}";
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
  // Open the conversation history sidebar
  Builder(
    builder: (context) => IconButton(
      icon: const Icon(Icons.history),
      tooltip: "Chat History",
      onPressed: () {
        Scaffold.of(context).openDrawer();
      },
    ),
  ),

  // Start a new conversation
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
            _styleChips(),
            _styleStatus(),
            Expanded(
              child: _messages.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              widget.icon,
                              size: 58,
                              color: widget.accentColor,
                            ),
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
                        final answeredAs = _answeredAsLabel(msg);
                        return Align(
                          alignment: msg.isUser
                              ? Alignment.centerRight
                              : Alignment.centerLeft,
                          child: Container(
                            margin: const EdgeInsets.symmetric(vertical: 6),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 12,
                            ),
                            constraints: BoxConstraints(
                              maxWidth:
                                  MediaQuery.of(context).size.width * 0.78,
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
                                if (answeredAs != null)
                                  Padding(
                                    padding: const EdgeInsets.only(bottom: 4),
                                    child: Text(
                                      answeredAs,
                                      style: const TextStyle(
                                        fontSize: 11,
                                        color: AppColors.muted,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ),
                                if (!msg.isUser && msg.hasCaution)
                                  Padding(
                                    padding: const EdgeInsets.only(bottom: 6),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        const Icon(
                                          Icons.warning_amber_rounded,
                                          size: 16,
                                          color: Color(0xFFE99A1E),
                                        ),
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
                                    color: msg.isUser
                                        ? Colors.white
                                        : AppColors.text,
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
                          borderRadius: BorderRadius.circular(25),
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 12,
                        ),
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